import argparse
import json
from pathlib import Path

from analyzer.service import get_regression_summary, run_diagnosis
from pipeline.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 1 document pipeline.")
    parser.add_argument(
        "--document",
        required=True,
        help="Path to input document text file.",
    )
    parser.add_argument(
        "--document-id",
        default=None,
        help="Optional explicit document id (defaults to filename stem).",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run judge + root-cause diagnosis and eval capture.",
    )
    args = parser.parse_args()

    doc_path = Path(args.document)
    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")

    text = doc_path.read_text(encoding="utf-8")
    document_id = args.document_id or doc_path.stem
    result = run_pipeline(document_id=document_id, text=text)
    output = {"pipeline_result": result.model_dump()}

    if args.analyze:
        diagnosis, eval_row = run_diagnosis(
            document_id=document_id,
            document_text=text,
            pipeline_result=result,
        )
        output["diagnosis"] = diagnosis.model_dump()
        output["eval_row"] = eval_row
        output["regression"] = get_regression_summary()

    print(json.dumps(output, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

