import streamlit as st
import pandas as pd
import os
import tempfile
from dotenv import load_dotenv
from karo.prompts.system_prompt_builder import SystemPromptBuilder
from rich.console import Console
from pydantic import Field
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(dotenv_path=dotenv_path)

# Import Karo components
from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.providers.anthropic_provider import AnthropicProvider, AnthropicProviderConfig
from karo.schemas.base_schemas import BaseInputSchema, BaseOutputSchema, AgentErrorSchema

# Import from examples module - adjust this path to match your project structure
from karo.tools.excel_reader_tool import ExcelReaderInput, ExcelReaderTool

# Initialize console for rich output
console = Console()

# Set page configuration
st.set_page_config(
    page_title="Excel Summarizer with Karo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📊 Excel File Summarizer with Karo Framework")
st.markdown("""
This app demonstrates how to use the Karo framework to analyze and summarize Excel files.
Upload a file and watch as the framework's tools and LLM agents generate insights!

> **Note**: This tool works best with smaller Excel files (less than 10MB) as it processes data in-memory.
""")

# Define a specific output schema for the summarization
class SummarizationOutput(BaseOutputSchema):
    summary: str = Field(..., description="A concise summary of the provided data.")
    key_takeaways: List[str] = Field(default_factory=list, description="A list of key points or takeaways from the data.")

# Sidebar
with st.sidebar:
    st.header("About Karo Framework")
    st.info(
        """
        Karo is a powerful framework for building AI applications with:
        * Modular tools with well-defined schemas
        * Agent-based architecture
        * Multiple LLM provider support
        
        This app demonstrates how to use Karo with Streamlit for deployment!
        """
    )
    
    st.header("Settings")
    provider_type = st.selectbox(
        "Provider",
        ["OpenAI", "Anthropic"],
        help="Select which LLM provider to use"
    )
    
    if provider_type == "OpenAI":
        api_key = st.text_input("OpenAI API Key", type="password", 
                               help="Enter your OpenAI API key to enable summarization")
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        model_choice = st.selectbox(
            "AI Model",
            ["gpt-4-turbo", "gpt-4o-mini", "gpt-3.5-turbo"],
            help="Select which OpenAI model to use for summarization"
        )
    else:  # Anthropic
        api_key = st.text_input("Anthropic API Key", type="password", 
                               help="Enter your Anthropic API key to enable summarization")
        
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        model_choice = st.selectbox(
            "AI Model",
            ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            help="Select which Anthropic model to use for summarization"
        )
    
    max_rows = st.slider("Max Rows to Process", 10, 500, 100, 
                        help="Limit the number of rows to process (higher = more complete but slower)")
    
    max_cols = st.slider("Max Columns to Process", 5, 50, 20,
                        help="Limit the number of columns to process")
    
    show_debug = st.checkbox("Show Debug Information", value=False,
                           help="Show system prompts and messages being sent to the LLM")

def run_summarization(file_path, max_rows, max_cols, provider_type="OpenAI", model="gpt-4-turbo", show_debug=False):
    """
    Run the Excel summarization process using Karo framework.
    
    Args:
        file_path: Path to the Excel file to summarize
        max_rows: Maximum number of rows to process
        max_cols: Maximum number of columns to process
        provider_type: 'OpenAI' or 'Anthropic'
        model: The model to use
        show_debug: Whether to display debug information
    """
    # Check for API key
    if provider_type == "OpenAI":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OpenAI API Key not found. Please enter your API key in the sidebar.")
            return None
    else:  # Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("Anthropic API Key not found. Please enter your API key in the sidebar.")
            return None
    
    # Initialize Excel reader tool
    with st.spinner("Initializing Excel Reader Tool..."):
        excel_reader = ExcelReaderTool()
        st.success("✅ ExcelReaderTool Initialized")
    
    # Run the tool to read Excel file
    with st.spinner("Reading Excel file..."):
        tool_input = ExcelReaderInput(
            file_path=file_path,
            max_rows=max_rows,
            max_cols=max_cols
        )
        tool_output = excel_reader.run(tool_input)
    
    # Check if Excel reading was successful
    if not tool_output.success:
        st.error(f"Error reading Excel file: {tool_output.error_message}")
        return None
    
    # Check if we got a data preview
    if not tool_output.data_preview:
        st.warning("No data preview available.")
        return None
    
    st.success(f"✅ Successfully read sheet '{tool_output.sheet_name_read}' ({tool_output.row_count} rows, {len(tool_output.column_names)} cols)")
    st.markdown("### Data Preview")
    st.markdown(tool_output.data_preview)
    
    # Initialize LLM provider
    with st.spinner(f"Initializing {provider_type} Provider..."):
        if provider_type == "OpenAI":
            provider_config = OpenAIProviderConfig(model=model)
            provider = OpenAIProvider(config=provider_config)
        else:  # Anthropic
            provider_config = AnthropicProviderConfig(model=model)
            provider = AnthropicProvider(config=provider_config)
        
        st.success(f"✅ {provider_type} Provider Initialized (Model: {model})")
    
    # Define system prompt
    system_prompt_content = "You are an expert data analyst. Your task is to analyze Excel data and provide accurate summaries and insights."
    
    # Create system prompt builder object
    system_prompt_builder = SystemPromptBuilder(role_description=system_prompt_content)
    
    # Create message for analysis
    data_message = (
        "Please analyze this Excel data:\n\n"
        "Data Preview:\n"
        "```markdown\n"
        f"{tool_output.data_preview}\n"
        "```\n\n"
        f"Column Names: {', '.join(tool_output.column_names)}\n"
        f"Sheet Name: {tool_output.sheet_name_read}\n"
        f"(Note: Only the first {tool_output.row_count} rows are shown in the preview)\n\n"
        "Generate a summary that specifically analyzes the data patterns. "
        "Include insights about key metrics and patterns visible in the data."
    )
    
    # Show debug information if requested
    if show_debug:
        st.markdown("### Debug Information")
        st.markdown("#### System Prompt")
        st.code(system_prompt_content)
        st.markdown("#### User Message")
        st.code(data_message)
    
    # Configure the agent
    with st.spinner("Configuring Karo Agent..."):
        agent_config = BaseAgentConfig(
            provider_config=provider_config,
            system_prompt=system_prompt_builder,
            output_schema=SummarizationOutput
        )
        
        # Initialize the agent
        summarization_agent = BaseAgent(config=agent_config)
        st.success("✅ Summarization Agent Configured")
    
    # Prepare history with our data message
    external_history = [
        {"role": "user", "content": data_message}
    ]
    
    # Run the agent
    with st.spinner(f"Generating summary using {provider_type} Agent..."):
        # Create a simple input (message content will come from history)
        simple_input = BaseInputSchema(chat_message="")
        
        # Run the agent with external history
        result = summarization_agent.run(
            input_data=simple_input,
            history=external_history
        )
    
    return result

# Main app flow
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Create a temporary file for the uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_filepath = tmp_file.name
    
    try:
        # Display file info
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Check if API key is provided
        api_var = "OPENAI_API_KEY" if provider_type == "OpenAI" else "ANTHROPIC_API_KEY"
        if api_var not in os.environ or not os.environ[api_var]:
            st.warning(f"Please enter your {provider_type} API key in the sidebar to enable Karo Agent summarization.")
        else:
            # Button to trigger summarization
            if st.button("Generate Summary with Karo"):
                # Run the Karo-based summarization
                result = run_summarization(
                    tmp_filepath, 
                    max_rows,
                    max_cols,
                    provider_type=provider_type,
                    model=model_choice,
                    show_debug=show_debug
                )
                
                # Process the result
                if result is None:
                    # Error was already displayed in run_summarization
                    pass
                elif isinstance(result, SummarizationOutput):
                    # Display the summary
                    st.subheader("📝 Summary")
                    st.write(result.summary)
                    
                    # Display key takeaways
                    st.subheader("🔑 Key Takeaways")
                    for i, takeaway in enumerate(result.key_takeaways, 1):
                        st.markdown(f"**{i}.** {takeaway}")
                elif isinstance(result, AgentErrorSchema):
                    st.error(f"Error from Karo Agent: {result.error_message}")
                else:
                    st.warning(f"Unexpected result type from Karo Agent: {type(result)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_filepath):
            os.unlink(tmp_filepath)
else:
    # Display a welcome message when no file is uploaded
    st.info("👈 Upload an Excel file using the file uploader to get started with Karo!")
    
    # Show a placeholder for the summary area
    st.subheader("Karo Agent Summary will appear here")
    st.text("Upload a file and click 'Generate Summary with Karo' to analyze your data.")