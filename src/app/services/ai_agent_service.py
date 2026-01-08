"""AI Agent service with MCP-style tools for wind farm analysis."""

import json
import os
from typing import Any

from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wind_energy_unit import WindFarm, WindTurbineFleet, WindFarmGenerationRecord
from app.models.forecast import WindGenerationForecast


# MCP-style tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_wind_farms",
            "description": "Get all wind farms belonging to the current user. Returns farm names, IDs, total capacity, and number of turbines.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wind_farm_details",
            "description": "Get detailed information about a specific wind farm including turbine fleets, locations, and specifications. Use get_user_wind_farms first to find the numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_farm_id": {
                        "type": "integer",
                        "description": "The numeric ID of the wind farm (from get_user_wind_farms)",
                    },
                },
                "required": ["wind_farm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecasts",
            "description": "Get generation forecasts for a wind farm for a specific time horizon. Returns hourly forecast data including predicted generation (kW) and weather conditions (wind speed, direction, temperature). Use get_user_wind_farms first to find the numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_farm_id": {
                        "type": "integer",
                        "description": "The numeric ID of the wind farm (from get_user_wind_farms)",
                    },
                    "horizon_hours": {
                        "type": "integer",
                        "description": "Forecast horizon in hours from now (default 48 hours, max 168 hours/7 days)",
                    },
                    "start_hours_from_now": {
                        "type": "integer",
                        "description": "Start time offset in hours from now (default 0, use 24 for tomorrow)",
                    },
                },
                "required": ["wind_farm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast_errors",
            "description": "Calculate forecast accuracy metrics (MAE, RMSE, MAPE, bias) by comparing forecasts with actual generation data for a wind farm. Use get_user_wind_farms first to find the numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_farm_id": {
                        "type": "integer",
                        "description": "The numeric ID of the wind farm (from get_user_wind_farms)",
                    },
                },
                "required": ["wind_farm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_generation_summary",
            "description": "Get a summary of actual generation data for a wind farm including total generation, average, and time range. Use get_user_wind_farms first to find the numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_farm_id": {
                        "type": "integer",
                        "description": "The numeric ID of the wind farm (from get_user_wind_farms)",
                    },
                },
                "required": ["wind_farm_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "regenerate_forecast",
            "description": "Regenerate the forecast for a wind farm with a specific time resolution (granularity). Use this when the user wants 15-minute forecasts instead of hourly. IMPORTANT: 15-minute forecasts are limited to 24 hours from now. For 'tomorrow' requests with 15-min data, use forecast_hours=48 to ensure coverage, then query with get_forecasts using start_hours_from_now to filter tomorrow's data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_farm_id": {
                        "type": "integer",
                        "description": "The numeric ID of the wind farm (from get_user_wind_farms)",
                    },
                    "granularity": {
                        "type": "string",
                        "enum": ["15min", "30min", "60min"],
                        "description": "Forecast time resolution: 15min (24hr limit), 30min, or 60min (hourly)",
                    },
                    "forecast_hours": {
                        "type": "integer",
                        "description": "Number of hours to forecast ahead from now (default 48, max 168). Note: 15-min data limited to 24 hours.",
                    },
                },
                "required": ["wind_farm_id", "granularity"],
            },
        },
    },
]


class AIAgentService:
    """AI Agent that can answer questions about wind farms using MCP-style tools."""

    def __init__(self) -> None:
        """Initialize the AI agent with Groq client."""
        from app.core.config import settings
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        self.client = Groq(api_key=api_key)
        # Primary model - best quality
        self.primary_model = "llama-3.3-70b-versatile"
        # Backup model - used when primary hits rate limit
        self.backup_model = "llama-3.1-8b-instant"
        self.model = self.primary_model

    async def _get_user_wind_farms(
        self, session: AsyncSession, user_id: int
    ) -> list[dict[str, Any]]:
        """Get all wind farms for a user."""
        stmt = (
            select(WindFarm)
            .options(selectinload(WindFarm.wind_turbine_fleets).selectinload(WindTurbineFleet.wind_turbine))
            .where(WindFarm.user_id == user_id)
        )
        result = await session.execute(stmt)
        farms = result.scalars().all()

        farm_list = []
        for farm in farms:
            total_turbines = sum(f.number_of_turbines for f in farm.wind_turbine_fleets)
            total_capacity = sum(
                f.number_of_turbines * (f.wind_turbine.nominal_power if f.wind_turbine else 0)
                for f in farm.wind_turbine_fleets
            )
            farm_list.append({
                "id": farm.id,
                "name": farm.name,
                "description": farm.description,
                "total_turbines": total_turbines,
                "total_capacity_mw": round(total_capacity, 2),
                "created_at": farm.created_at.isoformat() if farm.created_at else None,
            })
        return farm_list

    async def _get_wind_farm_details(
        self, session: AsyncSession, user_id: int, wind_farm_id: int
    ) -> dict[str, Any] | None:
        """Get detailed info about a wind farm."""
        stmt = (
            select(WindFarm)
            .options(
                selectinload(WindFarm.wind_turbine_fleets)
                .selectinload(WindTurbineFleet.wind_turbine),
                selectinload(WindFarm.wind_turbine_fleets)
                .selectinload(WindTurbineFleet.location),
            )
            .where(WindFarm.id == wind_farm_id, WindFarm.user_id == user_id)
        )
        result = await session.execute(stmt)
        farm = result.scalars().first()

        if not farm:
            return None

        fleets = []
        for f in farm.wind_turbine_fleets:
            fleets.append({
                "number_of_turbines": f.number_of_turbines,
                "turbine_type": f.wind_turbine.turbine_type if f.wind_turbine else None,
                "nominal_power_mw": f.wind_turbine.nominal_power if f.wind_turbine else None,
                "hub_height_m": f.wind_turbine.hub_height if f.wind_turbine else None,
                "location": {
                    "latitude": f.location.latitude if f.location else None,
                    "longitude": f.location.longitude if f.location else None,
                } if f.location else None,
            })

        return {
            "id": farm.id,
            "name": farm.name,
            "description": farm.description,
            "turbine_fleets": fleets,
            "total_turbines": sum(f.number_of_turbines for f in farm.wind_turbine_fleets),
            "total_capacity_mw": sum(
                f.number_of_turbines * (f.wind_turbine.nominal_power if f.wind_turbine else 0)
                for f in farm.wind_turbine_fleets
            ),
        }

    async def _get_forecasts(
        self,
        session: AsyncSession,
        user_id: int,
        wind_farm_id: int,
        horizon_hours: int = 48,
        start_hours_from_now: int = 0,
    ) -> dict[str, Any]:
        """Get forecasts for a wind farm within a time horizon.
        
        Args:
            session: Database session
            user_id: Current user ID
            wind_farm_id: Wind farm ID
            horizon_hours: Number of hours to forecast (default 48)
            start_hours_from_now: Start offset from now in hours (0 = now, 24 = tomorrow)
        """
        from datetime import datetime, timedelta, timezone
        
        # Verify ownership and get farm name
        farm_stmt = select(WindFarm).where(WindFarm.id == wind_farm_id, WindFarm.user_id == user_id)
        farm_result = await session.execute(farm_stmt)
        farm = farm_result.scalars().first()
        if not farm:
            return {"error": "Wind farm not found or access denied"}

        # Calculate time range
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(hours=start_hours_from_now)
        end_time = start_time + timedelta(hours=min(horizon_hours, 168))  # Max 7 days

        stmt = (
            select(WindGenerationForecast)
            .where(
                WindGenerationForecast.wind_farm_id == wind_farm_id,
                WindGenerationForecast.forecast_time >= start_time,
                WindGenerationForecast.forecast_time <= end_time,
            )
            .order_by(WindGenerationForecast.forecast_time.asc())
        )
        result = await session.execute(stmt)
        forecasts = list(result.scalars().all())

        if not forecasts:
            return {
                "wind_farm_id": wind_farm_id,
                "wind_farm_name": farm.name,
                "message": f"No forecast data available for the requested period ({start_time.isoformat()} to {end_time.isoformat()})",
                "forecast_count": 0,
            }

        # Calculate summary statistics
        generations = [f.generation for f in forecasts if f.generation is not None]
        wind_speeds = [f.wind_speed for f in forecasts if f.wind_speed is not None]
        
        hourly_forecasts = [
            {
                "time": f.forecast_time.strftime("%Y-%m-%d %H:%M"),
                "generation_kw": round(f.generation, 2) if f.generation else 0,
                "wind_speed_ms": round(f.wind_speed, 2) if f.wind_speed else None,
                "wind_direction_deg": round(f.wind_direction, 1) if f.wind_direction else None,
                "temperature_c": round(f.temperature, 1) if f.temperature else None,
            }
            for f in forecasts
        ]

        return {
            "wind_farm_id": wind_farm_id,
            "wind_farm_name": farm.name,
            "forecast_period": {
                "start": start_time.strftime("%Y-%m-%d %H:%M UTC"),
                "end": end_time.strftime("%Y-%m-%d %H:%M UTC"),
                "horizon_hours": horizon_hours,
            },
            "summary": {
                "total_forecasts": len(forecasts),
                "avg_generation_kw": round(sum(generations) / len(generations), 2) if generations else 0,
                "max_generation_kw": round(max(generations), 2) if generations else 0,
                "min_generation_kw": round(min(generations), 2) if generations else 0,
                "total_generation_mwh": round(sum(generations) / 1000, 2) if generations else 0,
                "avg_wind_speed_ms": round(sum(wind_speeds) / len(wind_speeds), 2) if wind_speeds else 0,
            },
            "hourly_forecasts": hourly_forecasts,
        }

    async def _get_forecast_errors(
        self, session: AsyncSession, user_id: int, wind_farm_id: int
    ) -> dict[str, Any]:
        """Calculate forecast errors by comparing with actual generation."""
        # Verify ownership
        farm_stmt = select(WindFarm).where(WindFarm.id == wind_farm_id, WindFarm.user_id == user_id)
        farm_result = await session.execute(farm_stmt)
        farm = farm_result.scalars().first()
        if not farm:
            return {"error": "Wind farm not found or access denied"}

        # Get forecasts
        forecast_stmt = (
            select(WindGenerationForecast)
            .where(WindGenerationForecast.wind_farm_id == wind_farm_id)
        )
        forecast_result = await session.execute(forecast_stmt)
        forecasts = forecast_result.scalars().all()

        # Get actual generation
        gen_stmt = (
            select(WindFarmGenerationRecord)
            .where(WindFarmGenerationRecord.wind_farm_id == wind_farm_id)
        )
        gen_result = await session.execute(gen_stmt)
        actuals = gen_result.scalars().all()

        if not forecasts or not actuals:
            return {
                "wind_farm_id": wind_farm_id,
                "wind_farm_name": farm.name,
                "error": "Insufficient data for error calculation",
                "forecast_count": len(forecasts),
                "actual_count": len(actuals),
            }

        # Match forecasts with actuals by hour
        forecast_by_hour = {
            f.forecast_time.replace(minute=0, second=0, microsecond=0): f.generation
            for f in forecasts if f.generation is not None
        }
        actual_by_hour = {
            a.timestamp.replace(minute=0, second=0, microsecond=0): a.generation
            for a in actuals if a.generation is not None
        }

        # Find matching hours
        matched_hours = set(forecast_by_hour.keys()) & set(actual_by_hour.keys())

        if len(matched_hours) < 2:
            return {
                "wind_farm_id": wind_farm_id,
                "wind_farm_name": farm.name,
                "error": "Not enough overlapping time points",
                "matched_hours": len(matched_hours),
            }

        # Calculate errors
        errors = []
        for hour in matched_hours:
            forecast_val = forecast_by_hour[hour]
            actual_val = actual_by_hour[hour]
            errors.append({
                "forecast": forecast_val,
                "actual": actual_val,
                "error": forecast_val - actual_val,
                "abs_error": abs(forecast_val - actual_val),
                "pct_error": abs(forecast_val - actual_val) / actual_val * 100 if actual_val > 0 else None,
            })

        # Calculate metrics
        n = len(errors)
        mae = sum(e["abs_error"] for e in errors) / n
        rmse = (sum(e["error"] ** 2 for e in errors) / n) ** 0.5
        bias = sum(e["error"] for e in errors) / n

        pct_errors = [e["pct_error"] for e in errors if e["pct_error"] is not None]
        mape = sum(pct_errors) / len(pct_errors) if pct_errors else None

        avg_actual = sum(e["actual"] for e in errors) / n
        avg_forecast = sum(e["forecast"] for e in errors) / n

        return {
            "wind_farm_id": wind_farm_id,
            "wind_farm_name": farm.name,
            "matched_hours": n,
            "metrics": {
                "mae_kw": round(mae, 2),
                "rmse_kw": round(rmse, 2),
                "mape_percent": round(mape, 2) if mape else None,
                "bias_kw": round(bias, 2),
                "bias_direction": "over-forecasting" if bias > 0 else "under-forecasting",
            },
            "summary": {
                "avg_actual_kw": round(avg_actual, 2),
                "avg_forecast_kw": round(avg_forecast, 2),
                "total_actual_mwh": round(sum(e["actual"] for e in errors) / 1000, 2),
                "total_forecast_mwh": round(sum(e["forecast"] for e in errors) / 1000, 2),
            },
        }

    async def _get_generation_summary(
        self, session: AsyncSession, user_id: int, wind_farm_id: int
    ) -> dict[str, Any]:
        """Get generation data summary for a wind farm."""
        # Verify ownership
        farm_stmt = select(WindFarm).where(WindFarm.id == wind_farm_id, WindFarm.user_id == user_id)
        farm_result = await session.execute(farm_stmt)
        farm = farm_result.scalars().first()
        if not farm:
            return {"error": "Wind farm not found or access denied"}

        gen_stmt = (
            select(WindFarmGenerationRecord)
            .where(WindFarmGenerationRecord.wind_farm_id == wind_farm_id)
            .order_by(WindFarmGenerationRecord.timestamp)
        )
        gen_result = await session.execute(gen_stmt)
        records = gen_result.scalars().all()

        if not records:
            return {
                "wind_farm_id": wind_farm_id,
                "wind_farm_name": farm.name,
                "message": "No generation data available",
            }

        generations = [r.generation for r in records if r.generation is not None]

        return {
            "wind_farm_id": wind_farm_id,
            "wind_farm_name": farm.name,
            "record_count": len(records),
            "time_range": {
                "start": records[0].timestamp.isoformat(),
                "end": records[-1].timestamp.isoformat(),
            },
            "generation_stats": {
                "total_mwh": round(sum(generations) / 1000, 2),
                "avg_kw": round(sum(generations) / len(generations), 2) if generations else 0,
                "max_kw": round(max(generations), 2) if generations else 0,
                "min_kw": round(min(generations), 2) if generations else 0,
            },
            "synthetic_count": sum(1 for r in records if r.is_synthetic),
            "real_count": sum(1 for r in records if not r.is_synthetic),
        }

    async def _regenerate_forecast(
        self,
        session: AsyncSession,
        user_id: int,
        wind_farm_id: int,
        granularity: str = "60min",
        forecast_hours: int = 48,
    ) -> dict[str, Any]:
        """Regenerate forecast for a wind farm with specific granularity."""
        from app.models import GranularityEnum
        from app.services.forecast_service import ForecastService
        
        # Verify ownership
        farm_stmt = select(WindFarm).where(WindFarm.id == wind_farm_id, WindFarm.user_id == user_id)
        farm_result = await session.execute(farm_stmt)
        farm = farm_result.scalars().first()
        if not farm:
            return {"error": "Wind farm not found or access denied"}

        # Map granularity string to enum
        granularity_map = {
            "15min": GranularityEnum.min_15,
            "30min": GranularityEnum.min_30,
            "60min": GranularityEnum.min_60,
        }
        granularity_enum = granularity_map.get(granularity, GranularityEnum.min_60)

        try:
            service = ForecastService(session)
            result = await service.generate_forecast(
                wind_farm_id=wind_farm_id,
                forecast_hours=min(forecast_hours, 168),  # Max 7 days
                granularity=granularity_enum,
                weather_model="best_match",
            )
            await session.commit()

            return {
                "success": True,
                "wind_farm_id": wind_farm_id,
                "wind_farm_name": farm.name,
                "message": f"Forecast regenerated with {granularity} resolution",
                "records_created": result.records_created,
                "forecast_period": {
                    "start": result.forecast_start.isoformat(),
                    "end": result.forecast_end.isoformat(),
                },
                "granularity": granularity,
                "total_forecasted_mwh": round(result.total_forecasted_generation_kwh / 1000, 2),
            }
        except Exception as e:
            return {"error": f"Failed to regenerate forecast: {str(e)}"}

    async def _execute_tool(
        self, tool_name: str, arguments: dict[str, Any], session: AsyncSession, user_id: int
    ) -> str:
        """Execute a tool and return the result as a string."""
        try:
            if tool_name == "get_user_wind_farms":
                result = await self._get_user_wind_farms(session, user_id)
            elif tool_name == "get_wind_farm_details":
                result = await self._get_wind_farm_details(
                    session, user_id, arguments["wind_farm_id"]
                )
            elif tool_name == "get_forecasts":
                result = await self._get_forecasts(
                    session,
                    user_id,
                    arguments["wind_farm_id"],
                    horizon_hours=arguments.get("horizon_hours", 48),
                    start_hours_from_now=arguments.get("start_hours_from_now", 0),
                )
            elif tool_name == "get_forecast_errors":
                result = await self._get_forecast_errors(
                    session, user_id, arguments["wind_farm_id"]
                )
            elif tool_name == "get_generation_summary":
                result = await self._get_generation_summary(
                    session, user_id, arguments["wind_farm_id"]
                )
            elif tool_name == "regenerate_forecast":
                result = await self._regenerate_forecast(
                    session,
                    user_id,
                    arguments["wind_farm_id"],
                    granularity=arguments.get("granularity", "60min"),
                    forecast_hours=arguments.get("forecast_hours", 48),
                )
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def chat(
        self,
        message: str,
        session: AsyncSession,
        user_id: int,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Process a chat message and return the response."""
        import logging
        logger = logging.getLogger(__name__)
        
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are an AI assistant for Koppen, a wind power forecasting platform. 
You help users understand their wind farm performance, forecast accuracy, and generation data.

You have access to tools that can:
- List the user's wind farms (returns farm IDs and names)
- Get detailed information about specific wind farms by ID
- Retrieve forecasts with hourly data by farm ID
- Calculate forecast errors (MAE, RMSE, MAPE, bias) by farm ID
- Summarize generation data by farm ID
- Regenerate forecasts with different time resolutions (15min, 30min, or 60min/hourly)

IMPORTANT RULES:
1. When the user asks about a specific wind farm by name, first use get_user_wind_farms to find the farm's numeric ID, then use that ID in subsequent tool calls.
2. All tools that require wind_farm_id expect an INTEGER, not a string name.
3. When showing forecasts, ALWAYS display the FULL TABLE of hourly_forecasts data in markdown table format. Never summarize to just one number.
4. Include ALL time periods from the hourly_forecasts array in your response table.
5. If the user asks for 15-minute forecasts and current data is hourly, use regenerate_forecast with granularity="15min" to create 15-minute resolution forecasts, then use get_forecasts to retrieve the new data.
6. When user asks for "tomorrow", regenerate forecast with forecast_hours=48 (to cover today and tomorrow), then use get_forecasts with start_hours_from_now=24 and horizon_hours=24 to get tomorrow's data.

When discussing forecast errors:
- MAE (Mean Absolute Error): Average absolute difference between forecast and actual
- RMSE (Root Mean Square Error): Penalizes larger errors more heavily
- MAPE (Mean Absolute Percentage Error): Error as a percentage
- Bias: Positive = over-forecasting, Negative = under-forecasting

Only access data for wind farms belonging to the current user.""",
            }
        ]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)

        # Add user message
        messages.append({"role": "user", "content": message})

        try:
            # First API call with tools
            print(f"[CHAT] Calling Groq API for user message: {message[:50]}...", flush=True)
            print(f"[CHAT] Using model: {self.model}", flush=True)
            
            # Multi-turn tool calling loop
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                print(f"[CHAT] Iteration {iteration}", flush=True)
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        max_tokens=4096,
                    )
                except Exception as api_error:
                    error_str = str(api_error)
                    print(f"[CHAT] API error in iteration {iteration}: {error_str[:100]}", flush=True)
                    
                    # Check if it's a rate limit error on primary model - switch to backup
                    if ("rate_limit" in error_str.lower() or "429" in error_str) and self.model == self.primary_model:
                        print(f"[CHAT] Rate limit hit on {self.model}, switching to backup model {self.backup_model}", flush=True)
                        self.model = self.backup_model
                        # Retry with backup model
                        continue
                    
                    # If rate limit on backup too, return error
                    if ("rate_limit" in error_str.lower() or "429" in error_str):
                        raise api_error
                    
                    # For other errors, try without tool_choice
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            max_tokens=4096,
                        )
                        return response.choices[0].message.content or "I couldn't generate a response."
                    except Exception:
                        raise api_error

                response_message = response.choices[0].message
                print(f"[CHAT] Got response, tool_calls: {bool(response_message.tool_calls)}", flush=True)

                # Check if model wants to use tools
                if not response_message.tool_calls:
                    # No more tool calls, return the final response
                    return response_message.content or "I couldn't generate a response."

                # Convert response message to dict format for next API call
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in response_message.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    # Handle empty or malformed arguments
                    try:
                        function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                    except json.JSONDecodeError:
                        function_args = {}
                    print(f"[CHAT] Executing tool: {function_name} with args: {function_args}", flush=True)

                    # Execute the tool
                    tool_result = await self._execute_tool(
                        function_name, function_args, session, user_id
                    )
                    print(f"[CHAT] Tool result length: {len(tool_result)}", flush=True)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })
            
            # If we hit max iterations, get a final response without tools
            print("[CHAT] Max iterations reached, getting final response", flush=True)
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096,
            )
            return final_response.choices[0].message.content or "I couldn't generate a response."
            
        except Exception as e:
            print(f"[CHAT] Error: {str(e)}", flush=True)
            raise



