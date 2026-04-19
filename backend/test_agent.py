from agno.agent import Agent  
from agno.models.azure import AzureOpenAI  
from agno.team import Team  
from agno.tools.duckduckgo import DuckDuckGoTools  
from pydantic import BaseModel, Field  
from typing import List  
from agno.models.google import Gemini

from dotenv import load_dotenv  

load_dotenv()  
class CompanyInfo(BaseModel):  
    company_name: str = Field(..., description="Name of the company")  
    Ceo: str = Field(..., description="Name of the CEO")
    founded_year: int = Field(..., description="Year the company was founded")
    summary: str = Field(..., description="Summary of company research")  
    key_findings: List[str] = Field(..., description="Key research findings")
    products_services: List[str] = Field(..., description="List of products and services offered by the company")
    financials: str = Field(..., description="Financial information about the company")  
  
# Agent 1: Research Agent  
research_agent = Agent(  
    name="Company Researcher",  
    model=Gemini(id="gemini-2.5-flash-lite"),  
    role="Research companies and gather detailed information",  
    tools=[DuckDuckGoTools()],  
    instructions="Research the requested company thoroughly. Gather comprehensive information about the company. Focus on key business details, financials, and recent developments.",  
)  
  
# Agent 2: JSON Creator Agent    
json_creator = Agent(  
    name="JSON Creator",  
    model=Gemini(id="gemini-2.5-flash-lite"),  
    role="Structure research data into JSON format",  
    instructions="Take the research findings from the research agent. Structure all information into the required JSON format. Ensure data is properly organized and formatted.",  
)  
  
# Team with both separate agents  
company_team = Team(  
    name="Company Analysis Team",  
    mode="coordinate",  
    model=Gemini(id="gemini-2.5-flash-lite"),  
    members=[research_agent, json_creator],  
    instructions="First, have the research agent gather company information. Then, have the JSON creator structure the findings into JSON format. Ensure all research data is properly formatted.",  
    show_tool_calls=True,  
    markdown=True,  
    show_members_responses=True,  
)

if __name__ == "__main__":  
    # Search for Infosys  
    company_team.print_response("Research TCS company", stream=True)