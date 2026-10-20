from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    id: str
    category: str
    text: str


PROMPTS = (
    Prompt("coding", "coding", "Write Python merge sort with a short explanation and example."),
    Prompt("sql", "sql", "SQL: orders(id,customer_id,total,created_at). Return each customer's top 3 orders by total, breaking ties by id. Explain the query."),
    Prompt("ner", "ner", "Extract PERSON, ORG, LOCATION as JSON: Maya Chen joined Acme in London. Ravi Shah visited Paris for a meeting with Globex. Explain each entity."),
)


def validate_prompts():
    for prompt in PROMPTS:
        if not prompt.text.isascii() or len(prompt.text.encode()) > 256:
            raise ValueError("Built-in prompts must be ASCII and at most 256 bytes")
