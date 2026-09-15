"""
Chat with GitHub Repository — Preserved & Enhanced Entry Point
Integrates with the AI Software Engineering Agent backend.
"""
import os
import streamlit as st
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.manager_agent import ManagerAgent
from workflows.repo_intelligence import run_repo_intelligence_workflow

# Streamlit App
st.set_page_config(page_title="Chat with GitHub Repo 💬", page_icon="💬")
st.title("Chat with GitHub Repository 💬")
st.caption("This app allows you to chat with a GitHub Repo using OpenAI API and AI Agent Intelligence.")

# Get OpenAI API key & GitHub Token from user
col1, col2 = st.columns(2)
with col1:
    openai_access_token = st.text_input("OpenAI API Key", type="password")
with col2:
    github_access_token = st.text_input("GitHub Token", type="password", value=os.getenv("GITHUB_TOKEN", ""))

if openai_access_token:
    os.environ["OPENAI_API_KEY"] = openai_access_token

git_repo = st.text_input("Enter the GitHub Repo (owner/repo)", value="Tanish-o9/GitHub-COP-Agent")

if git_repo:
    mcp_tools = GitHubMCPTools(token=github_access_token)
    memory = RepoMemory(git_repo)

    prompt = st.text_input("Ask any question about the GitHub Repo")
    if prompt:
        tracer = AgentTracer(prompt)
        response = run_repo_intelligence_workflow(git_repo, prompt, mcp_tools, tracer, memory)
        st.markdown(response)

st.info("💡 For multi-agent features (PR review, issue fixing, security audits), run `streamlit run app.py`!")