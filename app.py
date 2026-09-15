"""
AI Software Engineering Agent — Phase 4 Streamlit Application
Unified interface featuring Multi-Agent Chat, Codebase RAG, Impact Analysis, Webhook Triage, Evaluation Benchmark Dashboard, and Health Diagnostics.
"""
import os
import streamlit as st
from github_mcp import GitHubMCPTools
from agent_tracer import AgentTracer
from repo_memory import RepoMemory
from agent_state import AgentState, WorkflowState
from human_approval import HumanApprovalRequest, ApprovalStatus
from rag_engine import CodebaseRAGEngine
from dependency_analyzer import DependencyAnalyzer
from event_router import EventRouter
from health_check import HealthCheckManager
from evidence_checker import EvidenceChecker
from prompt_injection_guard import PromptInjectionGuard
from eval.eval_runner import EvaluationRunner
from report_generator import ReportGenerator
from agents.manager_agent import ManagerAgent
from workflows.repo_intelligence import run_repo_intelligence_workflow
from workflows.issue_analyzer import run_issue_analyzer_workflow
from workflows.pr_reviewer import run_pr_reviewer_workflow
from workflows.test_generator import run_test_generator_workflow
from workflows.security_auditor import run_security_auditor_workflow
from workflows.change_impact import run_change_impact_workflow
from workflows.engineering_workflow import prepare_engineering_fix_stateful, execute_approved_engineering_fix_stateful

# Page Config
st.set_page_config(
    page_title="GitHub Cop Agent",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; }
    .approval-card { background-color: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px; padding: 16px; margin: 12px 0; }
    .metric-badge { background-color: #E8F5E9; border: 1px solid #A5D6A7; color: #1B5E20; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap !important;
        gap: 6px 10px !important;
        border-bottom: 1px solid #333 !important;
        padding-bottom: 8px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        white-space: normal !important;
        padding: 8px 14px !important;
        border-radius: 6px !important;
        background-color: rgba(255, 255, 255, 0.07) !important;
        margin-bottom: 4px !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1E88E5 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>🤖 GitHub Cop Agent</div>", unsafe_allow_html=True)
st.caption("Phase 4: Evaluation Benchmark ➔ Evidence Validation ➔ Health Checks ➔ Prompt Injection Defense ➔ Multi-Agent Workflow.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Workspace Settings")
    repo_input = st.text_input("GitHub Repository", value="Tanish-o9/GitHub-COP-Agent")
    branch_input = st.text_input("Target Branch", value="main")
    github_token = st.text_input("GitHub Token (PAT)", type="password", value=os.getenv("GITHUB_TOKEN", ""))
    
    st.markdown("---")
    st.subheader("🧠 LLM Configuration")
    llm_provider = st.selectbox("LLM Provider", ["OpenAI", "Ollama (Local)", "Custom API"])
    if llm_provider == "OpenAI":
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key

    st.markdown("---")
    st.subheader("📦 Repository Memory")
    if repo_input:
        memory = RepoMemory(repo_input, branch=branch_input)
        st.text_area("Memory Snapshot", memory.get_context_summary(), height=120, disabled=True)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None
if "latest_tracer" not in st.session_state:
    st.session_state.latest_tracer = None
if "latest_agent_state" not in st.session_state:
    st.session_state.latest_agent_state = None
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = CodebaseRAGEngine(repo_input, branch_input)

mcp_tools = GitHubMCPTools(token=github_token)

# Application Tabs
tab_chat, tab_engineering, tab_rag, tab_graph, tab_diff, tab_test_impact, tab_impact, tab_webhooks, tab_eval, tab_health, tab_ops, tab_load = st.tabs([
    "💬 Multi-Agent Workspace",
    "🛠️ AI Engineering Workspace",
    "🔍 Semantic RAG Search",
    "🏛️ Code Intelligence Graph",
    "⚡ Semantic Diff & Risk Engine",
    "🎯 Test Impact Intelligence",
    "⚡ Change Impact Analyzer",
    "🔔 GitHub Webhook Simulator",
    "📊 Evaluation Benchmark",
    "🩺 System Health Diagnostics",
    "⚙️ Operations Dashboard",
    "🚀 Load Testing Benchmark"
])

# --------------------------------------------------
# TAB 1: MULTI-AGENT WORKSPACE
# --------------------------------------------------
with tab_chat:
    if st.session_state.latest_agent_state:
        astate: AgentState = st.session_state.latest_agent_state
        st.info(f"📍 **Workflow Status**: `{astate.current_state.value}` | **Revisions**: `{astate.revision_count}/{astate.max_revisions}`")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_approval:
        req: HumanApprovalRequest = st.session_state.pending_approval
        st.markdown("<div class='approval-card'>", unsafe_allow_html=True)
        st.warning("⚠️ **Human Approval Checkpoint: Repository Write Operations**")
        st.markdown(f"**Target Repository**: `{req.repo_name}` | **Safe Feature Branch**: `{req.target_branch}`")
        st.markdown(f"**Summary of Changes**: {req.change_summary}")
        
        st.markdown("**Files to Change / Add**:")
        for f in req.files_to_change:
            st.markdown(f"- `{f}`")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Approve Changes & Create PR", type="primary"):
                req.approve()
                tracer = st.session_state.latest_tracer or AgentTracer("PR Execution")
                result_msg = execute_approved_engineering_fix_stateful(req, mcp_tools, tracer)
                st.session_state.messages.append({"role": "assistant", "content": result_msg})
                st.session_state.pending_approval = None
                st.rerun()
        with col2:
            if st.button("❌ Reject Changes"):
                req.reject()
                st.session_state.messages.append({"role": "assistant", "content": "⛔ **User rejected proposed changes.** Write operations cancelled."})
                st.session_state.pending_approval = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    user_prompt = st.chat_input("Ask a question, analyze an issue, review a PR, check impact, or request a fix...")
    if user_prompt:
        # Prompt Injection Defense Filter
        safe_prompt = PromptInjectionGuard.sanitize_untrusted_content(user_prompt)
        st.session_state.messages.append({"role": "user", "content": safe_prompt})
        with st.chat_message("user"):
            st.markdown(safe_prompt)

        tracer = AgentTracer(safe_prompt)
        st.session_state.latest_tracer = tracer
        memory = RepoMemory(repo_input, branch=branch_input)

        manager = ManagerAgent(tracer)
        classification = manager.classify_request(safe_prompt)
        workflow_type = classification["workflow"]
        params = classification["params"]

        with st.chat_message("assistant"):
            try:
                with st.status(f"🚀 Executing Pipeline: `{workflow_type}`", expanded=True) as status:
                    if workflow_type == "CHANGE_IMPACT":
                        target_file = params.get("target_file", "chat_github_llama3.py")
                        response_md = run_change_impact_workflow(repo_input, target_file, mcp_tools, tracer, memory)
                    elif workflow_type == "REPO_INTELLIGENCE":
                        response_md = run_repo_intelligence_workflow(repo_input, safe_prompt, mcp_tools, tracer, memory, branch=branch_input)
                    elif workflow_type == "ISSUE_ANALYSIS":
                        response_md = run_issue_analyzer_workflow(repo_input, params.get("issue_number", 1), mcp_tools, tracer, memory)
                    elif workflow_type == "PR_REVIEW":
                        response_md = run_pr_reviewer_workflow(repo_input, params.get("pr_number", 1), mcp_tools, tracer, memory)
                    elif workflow_type == "TEST_GENERATION":
                        response_md = run_test_generator_workflow(repo_input, safe_prompt, mcp_tools, tracer, memory)
                    elif workflow_type == "SECURITY_AUDIT":
                        response_md = run_security_auditor_workflow(repo_input, mcp_tools, tracer, memory)
                    elif workflow_type == "FULL_ENGINEERING_WORKFLOW":
                        agent_state = AgentState(user_request=safe_prompt, repo_name=repo_input, branch=branch_input, issue_number=params.get("issue_number"))
                        st.session_state.latest_agent_state = agent_state
                        updated_state = prepare_engineering_fix_stateful(agent_state, mcp_tools, tracer, memory)
                        response_md = f"### 📝 Implementation Plan Formulated\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(updated_state.implementation_plan)]) + "\n\nPlease review the Human Approval card above."
                        status.update(label="⏸️ Paused — Awaiting Human Approval", state="running")

                    if workflow_type != "FULL_ENGINEERING_WORKFLOW":
                        status.update(label="✅ Execution Complete", state="complete")

                # Evidence & Hallucination Guard Validation
                known_tree = [f["path"] for f in mcp_tools.get_repo_tree(repo_input, branch=branch_input, recursive=True)]
                ev_check = EvidenceChecker.validate_response(response_md, [], known_tree)
                final_md = ev_check["sanitized_response"]

                st.markdown(final_md)
                st.session_state.messages.append({"role": "assistant", "content": final_md})
            except Exception as ex:
                st.error(f"⚠️ **Execution Note**: {ex}\n\n*Tip: Enter a GitHub Personal Access Token (PAT) in the left sidebar for full GitHub REST API access.*")

# --------------------------------------------------
# TAB: AI ENGINEERING WORKSPACE
# --------------------------------------------------
with tab_engineering:
    st.subheader("🛠️ Autonomous AI Engineering Workspace")
    task_obj_input = st.text_input("Enter Engineering Objective", value="Fix authentication timeout error in auth module")
    autonomy_lvl = st.slider("Autonomy Level (0-4)", min_value=0, max_value=4, value=2)

    if st.button("🚀 Intake & Initialize Engineering Task", type="primary"):
        with st.spinner("Validating task contract and extracting acceptance criteria..."):
            from database.connection import SessionLocal
            from autonomous_engine import AutonomousEngineeringController

            db = SessionLocal()
            controller = AutonomousEngineeringController(db)
            res = controller.intake_task(
                tenant_id=1,
                repository_name=repo_input,
                objective=task_obj_input,
                autonomy_level=autonomy_lvl
            )
            db.close()

            st.success(f"Task Intaked Successfully: `{res['task_id']}`")
            st.markdown("### Verifiable Acceptance Criteria:")
            for c in res["criteria"]:
                st.markdown(f"- `[{c['status']}]` **{c['id']}**: {c['description']}")

# --------------------------------------------------
# TAB 2: SEMANTIC RAG SEARCH
# --------------------------------------------------
with tab_rag:
    st.subheader("🔍 Codebase RAG Semantic Search")
    if st.button("🔨 Index Repository Codebase", type="secondary"):
        with st.spinner("Scanning code files and extracting symbols..."):
            rag = CodebaseRAGEngine(repo_input, branch_input)
            chunk_count = rag.index_repository(mcp_tools, max_files=20)
            st.session_state.rag_engine = rag
            st.success(f"Indexed {chunk_count} code-aware chunks!")

    rag_query = st.text_input("Enter semantic query (e.g. 'Where is GITHUB_TOKEN loaded?')")
    if rag_query:
        rag: CodebaseRAGEngine = st.session_state.rag_engine
        results = rag.hybrid_search(rag_query, top_k=5)
        if results:
            st.markdown(f"### Found {len(results)} Relevant Results")
            for res in results:
                c = res["chunk"]
                with st.expander(f"⭐ Score: {res['score']} | Symbol: {c.symbol_name} ({c.file_path})"):
                    st.markdown(f"- **Citation**: {res['citation']}")
                    st.markdown(f"- **Line Range**: L{c.start_line}-L{c.end_line}")
                    st.code(c.content, language=c.language)

# --------------------------------------------------
# TAB 3: REPOSITORY CODE GRAPH
# --------------------------------------------------
with tab_graph:
    st.subheader("🏛️ Repository Code Intelligence Graph")
    from code_graph import CodeIntelligenceGraph
    from architecture_explainer import ArchitectureExplainer

    graph = CodeIntelligenceGraph(repo_input)
    explainer = ArchitectureExplainer(repo_input, code_graph=graph)

    if st.button("Build Code Intelligence Graph", type="primary"):
        with st.spinner("Parsing AST entities and building symbol linkages..."):
            views = explainer.generate_architecture_views(mcp_tools)
            st.markdown(f"### Executive Overview")
            st.write(views["executive_overview"])

            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("### Request Flow")
                for step in views["request_flow"]:
                    st.write(step)
            with c_b:
                st.markdown("### Data Flow")
                for step in views["data_flow"]:
                    st.write(step)

# --------------------------------------------------
# TAB 4: SEMANTIC DIFF & RISK ENGINE
# --------------------------------------------------
with tab_diff:
    st.subheader("⚡ Semantic Diff & Change Risk Engine")
    diff_input = st.text_area("Paste Git Diff text", height=150, value="""+def authenticate_user(token):\n+    if not token: return False\n+    return True""")
    
    if st.button("Evaluate Change Risk Score", type="primary"):
        from semantic_diff import SemanticDiffAnalyzer
        from risk_engine import ChangeRiskEngine

        diff_analyzer = SemanticDiffAnalyzer()
        summary = diff_analyzer.analyze_diff(diff_input)

        risk_engine = ChangeRiskEngine()
        report = risk_engine.evaluate_risk(summary)

        st.metric("Change Risk Score", f"{report.risk_score} / 100", delta=report.risk_level)
        st.markdown("### Explainable Risk Factors:")
        for r in report.reasons:
            st.warning(f"⚠️ {r}")

# --------------------------------------------------
# TAB 5: TEST IMPACT INTELLIGENCE
# --------------------------------------------------
with tab_test_impact:
    st.subheader("🎯 Test Impact & Coverage Intelligence")
    changed_target = st.text_input("Target changed file", value="api/routes_runs.py")

    if st.button("Analyze Test Impact", type="primary"):
        from test_impact import TestImpactAnalyzer
        analyzer = TestImpactAnalyzer()
        impact = analyzer.analyze_impact([changed_target])

        st.markdown(f"### Related Test Suites for `{changed_target}`:")
        for t in impact.related_tests:
            st.markdown(f"- `{t}`")

        st.markdown("### Recommended Actionable Steps:")
        for rec in impact.recommendations:
            st.info(f"💡 {rec}")






# Sidebar Observability Trace & Efficiency Metrics
if st.session_state.latest_tracer:
    with st.sidebar.expander("📊 Execution Metrics & Traces", expanded=False):
        tr = st.session_state.latest_tracer.get_summary()
        st.write(f"**Run ID**: `{tr['run_id']}`")
        st.write(f"**Elapsed**: `{tr['elapsed_sec']}s`")
        st.write(f"**Agent Calls**: `{tr['agent_calls']}` | **MCP Tool Calls**: `{tr['tool_calls']}`")
        st.write(f"**Files Read**: `{tr['files_read']}` | **RAG Chunks**: `{tr['retrieved_chunks']}`")
        st.write(f"**Revision Cycles**: `{tr['revision_cycles']}`")
        
        st.markdown("**Hierarchy Trace**:")
        for step in st.session_state.latest_tracer.steps:
            st.markdown(f"- `{step['timestamp']}` **{step['parent_agent']} ➔ {step['agent']}**: {step['action']}")

