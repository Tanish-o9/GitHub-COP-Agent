"""
Chat with GitHub Repo (Llama-3 & Ollama) — Preserved & Enhanced Entry Point
Integrates local Llama-3 / Ollama with the AI Software Engineering Agent backend.
"""
import os
import streamlit as st
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from workflows.repo_intelligence import run_repo_intelligence_workflow

# Streamlit App
st.set_page_config(page_title="Chat with GitHub Repo (Llama-3) 💬", page_icon="💬")
st.title("Chat with GitHub Repository (Llama-3) 💬")
st.caption("This app allows you to chat with a GitHub Repo using Llama-3 running with Ollama.")

# Environment configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

git_repo = st.text_input("Enter the GitHub Repo (owner/repo)", value="Tanish-o9/GitHub-COP-Agent")
prompt = st.text_input("Ask any question about the GitHub Repo")

if git_repo and prompt:
    mcp_tools = GitHubMCPTools(token=GITHUB_TOKEN)
    memory = RepoMemory(git_repo)
    tracer = AgentTracer(prompt)
    
    with st.spinner("Analyzing repository with Agent Intelligence..."):
        answer = run_repo_intelligence_workflow(git_repo, prompt, mcp_tools, tracer, memory)
        st.markdown(answer)

st.info("💡 For multi-agent features (PR review, issue fixing, security audits), run `streamlit run app.py`!")