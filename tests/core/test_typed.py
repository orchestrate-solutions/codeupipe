"""
Typed Tests for Opt-in Generics
Testing generic type features with codeupipe.
"""

from typing import List, TypedDict, Optional

import pytest

from codeupipe.core import Pipeline, Payload, Filter


class InputData(TypedDict):
    numbers: List[int]
    operation: str


class OutputData(InputData):
    result: float


class SumFilter(Filter[InputData, OutputData]):
    async def call(self, payload: Payload[InputData]) -> Payload[OutputData]:
        numbers = payload.get("numbers") or []
        total = sum(numbers)
        return payload.insert_as("result", float(total))  # type: ignore


class TestTypedBasics:
    @pytest.mark.unit
    def test_typed_payload_creation(self):
        """Test creating a typed payload."""
        data: InputData = {"numbers": [1, 2, 3], "operation": "sum"}
        p: Payload[InputData] = Payload(data)
        assert p.get("numbers") == [1, 2, 3]

    @pytest.mark.unit
    def test_typed_filter_execution(self):
        """Test executing a typed filter."""
        f = SumFilter()
        input_data: InputData = {"numbers": [1, 2, 3, 4], "operation": "sum"}
        p: Payload[InputData] = Payload(input_data)

        import asyncio
        result = asyncio.run(f.call(p))
        assert result.get("result") == 10.0

    @pytest.mark.unit
    def test_typed_pipeline_execution(self):
        """Test executing a typed pipeline."""
        pipeline: Pipeline[InputData, OutputData] = Pipeline()
        pipeline.add_filter(SumFilter())

        input_data: InputData = {"numbers": [2, 4, 6, 8], "operation": "stats"}
        p: Payload[InputData] = Payload(input_data)

        import asyncio
        result = asyncio.run(pipeline.run_async(p))
        assert result.get("result") == 20.0


class InitialData(TypedDict):
    name: str

class EvolvedData(TypedDict):
    name: str
    age: int

class SampleData(TypedDict):
    value: int

class SampleData2(TypedDict):
    counter: int


class TestGenericTypeEvolution:
    """Test generic type evolution features."""

    @pytest.mark.unit
    def test_payload_type_evolution(self):
        """Test that Payload supports type evolution with insert_as."""



        initial: InitialData = {"name": "Alice"}
        p: Payload[InitialData] = Payload(initial)

        evolved = p.insert_as("age", 30)

        assert evolved.get("name") == "Alice"
        assert evolved.get("age") == 30

    @pytest.mark.unit
    def test_generic_payload_operations(self):
        """Test generic Payload operations maintain type safety."""


        data: SampleData = {"value": 42}
        p: Payload[SampleData] = Payload(data)

        assert p.get("value") == 42
        assert p.get("missing") is None

        new_p = p.insert("new_field", "test")
        assert new_p.get("value") == 42
        assert new_p.get("new_field") == "test"

        other_data: SampleData = {"value": 100}
        other_p: Payload[SampleData] = Payload(other_data)
        merged = p.merge(other_p)
        assert merged.get("value") == 100

    @pytest.mark.unit
    def test_mutable_payload_generic(self):
        """Test MutablePayload with generic typing."""


        data: SampleData2 = {"counter": 0}
        mutable = Payload(data).with_mutation()

        mutable.set("counter", 5)  # type: ignore
        assert mutable.get("counter") == 5

        immutable = mutable.to_immutable()  # type: ignore
        assert immutable.get("counter") == 5


class RawData(TypedDict):
    raw_values: List[str]

class ParsedData(TypedDict):
    raw_values: List[str]
    parsed_numbers: List[int]

class ProcessedData(TypedDict):
    raw_values: List[str]
    parsed_numbers: List[int]
    sum: int
    average: float

class ParseFilter(Filter[RawData, ParsedData]):

    async def call(self, payload: Payload[RawData]) -> Payload[ParsedData]:
        raw_values = payload.get('raw_values') or []
        parsed_numbers = [int(x) for x in raw_values if x.isdigit()]
        return payload.insert_as('parsed_numbers', parsed_numbers)

class ProcessFilter(Filter[ParsedData, ProcessedData]):
    async def call(self, payload: Payload[ParsedData]) -> Payload[ProcessedData]:
        numbers = payload.get("parsed_numbers") or []
        total = sum(numbers)
        avg = total / len(numbers) if numbers else 0.0
        return payload.insert_as("sum", total).insert_as("average", avg)  # type: ignore


class InputData2(TypedDict):
    value: Optional[int]

class OutputData2(TypedDict):
    value: Optional[int]
    error: Optional[str]

class ValidateFilter(Filter[InputData2, OutputData2]):

    async def call(self, payload: Payload[InputData2]) -> Payload[OutputData2]:
        value = payload.get('value')
        if value is None:
            return payload.insert_as('error', 'Value is required')
        if not isinstance(value, int):
            return payload.insert_as('error', 'Value must be an integer')
        if value < 0:
            return payload.insert_as('error', 'Value must be non-negative')
        return payload.insert_as('error', None)


class TestTypedWorkflows:
    """Test complete typed workflows."""

    @pytest.mark.unit
    def test_typed_data_processing_pipeline(self):
        """Test a complete typed data processing pipeline."""





        pipeline: Pipeline = Pipeline()
        pipeline.add_filter(ParseFilter())
        pipeline.add_filter(ProcessFilter())

        input_data: RawData = {"raw_values": ["1", "2", "3", "4", "5"]}
        p: Payload[RawData] = Payload(input_data)

        import asyncio
        result = asyncio.run(pipeline.run_async(p))

        assert result.get("parsed_numbers") == [1, 2, 3, 4, 5]
        assert result.get("sum") == 15
        assert result.get("average") == 3.0

    @pytest.mark.unit
    def test_typed_error_handling(self):
        """Test typed error handling in workflows."""




        valid_input: InputData2 = {"value": 42}
        p: Payload[InputData2] = Payload(valid_input)

        f = ValidateFilter()
        import asyncio
        result = asyncio.run(f.call(p))
        assert result.get("error") is None

        invalid_input: InputData2 = {"value": -1}
        p2: Payload[InputData2] = Payload(invalid_input)
        result2 = asyncio.run(f.call(p2))
        assert result2.get("error") == "Value must be non-negative"


class SimpleFilter(Filter):

    async def call(self, payload: Payload) -> Payload:
        value = payload.get('input') or 0
        return payload.insert('output', value * 2)


class TestBackwardCompatibility:
    """Test that generic enhancements don't break untyped code."""

    @pytest.mark.unit
    def test_untyped_payload_still_works(self):
        """Test that untyped Payload usage still works."""
        p = Payload({"key": "value"})
        assert p.get("key") == "value"

        new_p = p.insert("new_key", "new_value")
        assert new_p.get("new_key") == "new_value"

    @pytest.mark.unit
    def test_mixed_typed_untyped_pipelines(self):
        """Test mixing typed and untyped components in pipelines."""


        pipeline = Pipeline()
        pipeline.add_filter(SimpleFilter())

        p = Payload({"input": 5})
        import asyncio
        result = asyncio.run(pipeline.run_async(p))
        assert result.get("output") == 10
