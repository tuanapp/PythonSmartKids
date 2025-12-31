import json
from app.services.performance_report_service import AnalystAgent, make_initial_state

def run_test():
    a = AnalystAgent()
    state = make_initial_state("test-uid")
    state["evidence_sufficient"] = True
    state["evidence_quality_score"] = 0.9
    state["hybrid_context"] = "Test hybrid context"
    result = a.generate_report(state)
    output = {
        "model_used": result.get("model_used"),
        "messages": result.get("messages"),
        "analysis_report_start": (result.get("analysis_report") or "")[:800]
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run_test()