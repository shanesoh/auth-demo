from faker import Faker
from fastapi import FastAPI
import random

app = FastAPI(
    title="c3n",
    docs_url="/"
)

faker = Faker()


@app.post("/queryAddress")
def query_address(ssn):
    """Query for addresses registered to the given social security number.
    """
    Faker.seed(ssn)
    random.seed(ssn)
    return [faker.address() for _ in range(random.randint(1, 5))]
