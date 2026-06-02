from pydantic_ai.models.test import TestModel

from app.agent_runtime import CloserAgentOutput, run_closer_agent


def test_closer_agent_runs_with_pydanticai_test_model(db_session):
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "summary": "Inquiry has enough details to score and draft a quote.",
            "draft_response": "Thanks, we can prepare pricing after confirming quantity.",
            "next_actions": ["score_inquiry", "calc_quote"],
            "requires_human_review": False,
        },
    )

    output = run_closer_agent(
        db_session,
        1,
        "Assess this inquiry and suggest next steps.",
        inquiry_id=123,
        model=model,
    )

    assert isinstance(output, CloserAgentOutput)
    assert output.summary.startswith("Inquiry has enough details")
    assert output.next_actions == ["score_inquiry", "calc_quote"]


def test_closer_agent_exposes_core_tools_to_model(db_session):
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "summary": "Ready.",
            "draft_response": None,
            "next_actions": [],
            "requires_human_review": False,
        },
    )

    run_closer_agent(db_session, 1, "List available operating tools.", model=model)

    tool_names = {tool.name for tool in model.last_model_request_parameters.function_tools}
    assert {
        "get_inquiry",
        "score_inquiry",
        "get_customer",
        "calc_quote",
        "generate_pi",
        "search_knowledge",
        "match_product",
        "send_message",
        "create_followup",
    }.issubset(tool_names)
