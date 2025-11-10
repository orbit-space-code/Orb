"""
Cost tracking and estimation for analysis sessions
"""
from typing import Dict, Any, List
from decimal import Decimal


class CostTracker:
    """Track and estimate costs for analysis sessions"""
    
    # Cost per 1000 lines analyzed (in USD)
    TOOL_COSTS = {
        "eslint": Decimal("0.001"),
        "pylint": Decimal("0.001"),
        "flake8": Decimal("0.001"),
        "bandit": Decimal("0.002"),
        "snyk": Decimal("0.005"),  # API calls cost
        "safety": Decimal("0.003"),
        "prettier": Decimal("0.001"),
        "black": Decimal("0.001"),
        "rubocop": Decimal("0.001"),
        "gitleaks": Decimal("0.002"),
        "semgrep": Decimal("0.003"),
    }
    
    # Base cost per analysis session
    BASE_COST = Decimal("0.01")
    
    @classmethod
    def estimate_cost(
        cls,
        tools: List[str],
        estimated_lines: int = 10000,
    ) -> Decimal:
        """
        Estimate cost for an analysis session
        
        Args:
            tools: List of tool names to run
            estimated_lines: Estimated lines of code
            
        Returns:
            Estimated cost in USD
        """
        cost = cls.BASE_COST
        
        for tool in tools:
            if tool in cls.TOOL_COSTS:
                # Cost = (lines / 1000) * cost_per_1000_lines
                tool_cost = (Decimal(estimated_lines) / 1000) * cls.TOOL_COSTS[tool]
                cost += tool_cost
        
        return cost.quantize(Decimal("0.0001"))
    
    @classmethod
    def calculate_actual_cost(
        cls,
        tool_results: List[Dict[str, Any]],
    ) -> Decimal:
        """
        Calculate actual cost based on tool execution
        
        Args:
            tool_results: List of tool result dictionaries
            
        Returns:
            Actual cost in USD
        """
        cost = cls.BASE_COST
        
        for result in tool_results:
            tool_name = result.get("name")
            lines_analyzed = result.get("lines_analyzed", 0)
            
            if tool_name in cls.TOOL_COSTS:
                tool_cost = (Decimal(lines_analyzed) / 1000) * cls.TOOL_COSTS[tool_name]
                cost += tool_cost
        
        return cost.quantize(Decimal("0.0001"))
    
    @classmethod
    def get_cost_breakdown(
        cls,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Get detailed cost breakdown
        
        Args:
            tool_results: List of tool result dictionaries
            
        Returns:
            Cost breakdown dictionary
        """
        breakdown = {
            "base_cost": float(cls.BASE_COST),
            "tools": {},
            "total": 0.0,
        }
        
        total = cls.BASE_COST
        
        for result in tool_results:
            tool_name = result.get("name")
            lines_analyzed = result.get("lines_analyzed", 0)
            
            if tool_name in cls.TOOL_COSTS:
                tool_cost = (Decimal(lines_analyzed) / 1000) * cls.TOOL_COSTS[tool_name]
                breakdown["tools"][tool_name] = {
                    "lines_analyzed": lines_analyzed,
                    "cost": float(tool_cost),
                }
                total += tool_cost
        
        breakdown["total"] = float(total.quantize(Decimal("0.0001")))
        
        return breakdown
    
    @classmethod
    def get_monthly_estimate(
        cls,
        sessions_per_month: int,
        avg_tools_per_session: int = 6,
        avg_lines_per_session: int = 10000,
    ) -> Dict[str, Any]:
        """
        Estimate monthly costs
        
        Args:
            sessions_per_month: Number of analysis sessions per month
            avg_tools_per_session: Average tools per session
            avg_lines_per_session: Average lines per session
            
        Returns:
            Monthly cost estimate
        """
        # Estimate using average tool cost
        avg_tool_cost = sum(cls.TOOL_COSTS.values()) / len(cls.TOOL_COSTS)
        
        cost_per_session = cls.BASE_COST + (
            (Decimal(avg_lines_per_session) / 1000) * 
            avg_tool_cost * 
            avg_tools_per_session
        )
        
        monthly_cost = cost_per_session * sessions_per_month
        
        return {
            "sessions_per_month": sessions_per_month,
            "cost_per_session": float(cost_per_session.quantize(Decimal("0.0001"))),
            "monthly_cost": float(monthly_cost.quantize(Decimal("0.01"))),
            "yearly_cost": float((monthly_cost * 12).quantize(Decimal("0.01"))),
        }
