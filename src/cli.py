import argparse
import asyncio
import sys

from services.chat import ChatService


async def ask(question: str) -> str:
    service = ChatService()
    session_id = service.create_session()
    return await service.send(session_id, question)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the AI assistant a question.")
    parser.add_argument("question", nargs="+", help="Question to send to the assistant")
    args = parser.parse_args()
    question = " ".join(args.question).strip()
    if not question:
        parser.error("Question must not be empty.")
    try:
        print(asyncio.run(ask(question)))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
