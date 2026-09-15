"""
CLI Entrypoint — Autonomous AI Software Engineering Platform
Interactive Terminal Interface for GitHub Repository Operations, Multi-Agent Chat, RAG, and Engineering Tasks.
"""
import os
import sys
import time
from typing import Optional
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agents.manager_agent import ManagerAgent
from workflows.repo_intelligence import run_repo_intelligence_workflow
from workflows.change_impact import run_change_impact_workflow
from workflows.issue_analyzer import run_issue_analyzer_workflow
from workflows.pr_reviewer import run_pr_reviewer_workflow
from rag_engine import CodebaseRAGEngine
from autonomous_engine import AutonomousEngineeringController
from database.connection import SessionLocal

def print_banner():
    print("=" * 65)
    print("🤖 GITHUB COP AGENT — TERMINAL CLI")
    print("=" * 65)

def main():
    print_banner()
    
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        token = input("🔑 Enter GitHub Personal Access Token (or press Enter to skip): ").strip()

    repo_name = input("📦 Enter Target GitHub Repository [default: Tanish-o9/GitHub-COP-Agent]: ").strip()
    if not repo_name:
        repo_name = "Tanish-o9/GitHub-COP-Agent"
    
    branch = input("🌿 Enter Target Branch [default: main]: ").strip()
    if not branch:
        branch = "main"

    mcp_tools = GitHubMCPTools(token=token)
    memory = RepoMemory(repo_name, branch=branch)
    rag_engine = CodebaseRAGEngine(repo_name, branch=branch)

    print(f"\n✅ Initialized session for '{repo_name}' (branch: '{branch}')\n")

    while True:
        print("-" * 65)
        print("Select an Option:")
        print("  [1] 💬 Ask Question / Chat with Repository")
        print("  [2] 🛠️ Intake Autonomous Engineering Task")
        print("  [3] ⚡ Change Impact Analysis")
        print("  [4] 🔍 RAG Codebase Search")
        print("  [5] 🐞 Analyze Issue")
        print("  [6] 🔍 Review Pull Request")
        print("  [7] 🧪 Run All Integration Tests")
        print("  [0] 🚪 Exit")
        print("-" * 65)

        choice = input("Enter option number (0-7): ").strip()

        if choice == "0":
            print("\n👋 Exiting Autonomous Engineering CLI. Goodbye!")
            sys.exit(0)

        elif choice == "1":
            prompt = input("\n💬 Enter question/prompt: ").strip()
            if prompt:
                print("\n⏳ Processing multi-agent workflow...")
                tracer = AgentTracer(prompt)
                manager = ManagerAgent(tracer)
                res = run_repo_intelligence_workflow(repo_name, prompt, mcp_tools, tracer, memory, branch=branch)
                print("\n" + "=" * 65)
                print("📋 AGENT RESPONSE:")
                print("=" * 65)
                print(res)
                print("=" * 65 + "\n")

        elif choice == "2":
            obj = input("\n🛠️ Enter Engineering Task Objective: ").strip()
            if obj:
                lvl_str = input("🎚️ Enter Autonomy Level (0-4) [default: 2]: ").strip()
                lvl = int(lvl_str) if lvl_str.isdigit() and 0 <= int(lvl_str) <= 4 else 2
                
                print(f"\n⏳ Initializing task intake with Autonomy Level {lvl}...")
                db = SessionLocal()
                try:
                    controller = AutonomousEngineeringController(db)
                    result = controller.intake_task(
                        tenant_id=1,
                        repository_name=repo_name,
                        objective=obj,
                        autonomy_level=lvl
                    )
                    print("\n" + "=" * 65)
                    print(f"✅ TASK INTAKED: {result['task_id']}")
                    print(f"📍 State: {result['state']}")
                    print("📋 Verifiable Acceptance Criteria:")
                    for c in result.get("criteria", []):
                        print(f"  - [{c['status']}] {c['id']}: {c['description']}")
                    print("=" * 65 + "\n")
                finally:
                    db.close()

        elif choice == "3":
            target_file = input("\n⚡ Enter target file path to analyze [default: chat_github_llama3.py]: ").strip()
            if not target_file:
                target_file = "chat_github_llama3.py"
            print(f"\n⏳ Analyzing change impact for '{target_file}'...")
            tracer = AgentTracer("Change Impact CLI")
            res = run_change_impact_workflow(repo_name, target_file, mcp_tools, tracer, memory)
            print("\n" + "=" * 65)
            print(res)
            print("=" * 65 + "\n")

        elif choice == "4":
            query = input("\n🔍 Enter RAG search query (e.g. 'Where is GITHUB_TOKEN loaded?'): ").strip()
            if query:
                print("\n⏳ Searching code index...")
                results = rag_engine.hybrid_search(query, top_k=3)
                print("\n" + "=" * 65)
                print(f"Found {len(results)} RAG Chunks:")
                for r in results:
                    c = r["chunk"]
                    print(f"\n⭐ Citation: {r['citation']} (Score: {r['score']})")
                    print(f"Symbol: {c.symbol_name} | Lines {c.start_line}-{c.end_line}")
                    print(c.content[:300] + ("..." if len(c.content) > 300 else ""))
                print("=" * 65 + "\n")

        elif choice == "5":
            iss_num = input("\n🐞 Enter Issue Number [default: 1]: ").strip()
            num = int(iss_num) if iss_num.isdigit() else 1
            print(f"\n⏳ Analyzing Issue #{num}...")
            tracer = AgentTracer(f"Issue #{num}")
            res = run_issue_analyzer_workflow(repo_name, num, mcp_tools, tracer, memory)
            print("\n" + "=" * 65)
            print(res)
            print("=" * 65 + "\n")

        elif choice == "6":
            pr_num = input("\n🔍 Enter PR Number [default: 1]: ").strip()
            num = int(pr_num) if pr_num.isdigit() else 1
            print(f"\n⏳ Reviewing PR #{num}...")
            tracer = AgentTracer(f"PR #{num}")
            res = run_pr_reviewer_workflow(repo_name, num, mcp_tools, tracer, memory)
            print("\n" + "=" * 65)
            print(res)
            print("=" * 65 + "\n")

        elif choice == "7":
            print("\n🧪 Running Phase 8 Integration Test Suite...")
            os.system(f'"{sys.executable}" scratch/test_phase8.py')

        else:
            print("\n⚠️ Invalid option. Please choose 0-7.")

if __name__ == "__main__":
    main()
