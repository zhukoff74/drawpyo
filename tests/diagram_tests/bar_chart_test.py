import pytest
from unittest.mock import Mock
from drawpyo.diagram_types.bar_chart import BarChart
from drawpyo.diagram.text_format import TextFormat
from drawpyo.diagram.objects import Object, Group


@pytest.fixture
def basic_data():
    return {"A": 10, "B": 20}


@pytest.fixture
def extended_data():
    return {"A": 10, "B": 20, "C": 15}


@pytest.fixture
def basic_chart(basic_data):
    return BarChart(basic_data)


class TestBarChartInitialization:
    """Test BarChart initialization and validation."""

    @pytest.mark.parametrize(
        "invalid_data,error_type,error_msg",
        [
            ({}, ValueError, "Data cannot be empty"),
            ([("A", 10), ("B", 20)], TypeError, "Data must be a dict"),
            ({"A": 10, "B": "20"}, TypeError, "must be numeric"),
        ],
    )
    def test_initialization_invalid_data(self, invalid_data, error_type, error_msg):
        with pytest.raises(error_type, match=error_msg):
            BarChart(invalid_data)

    @pytest.mark.parametrize(
        "data,colors,expected",
        [
            ({"A": 10, "B": 20}, "#ff0000", ["#ff0000", "#ff0000"]),
            (
                {"A": 10, "B": 20, "C": 15},
                ["#ff0000", "#00ff00"],
                ["#ff0000", "#00ff00", "#00ff00"],
            ),
            ({"A": 10}, [], ["#66ccff"]),
        ],
    )
    def test_initialization_color_handling(self, data, colors, expected):
        chart = BarChart(data, bar_colors=colors)
        assert chart._bar_colors == expected

    def test_initialization_with_custom_formatters(self):
        """Test custom label formatters."""
        data = {"A": 10}
        base_formatter = lambda l, v: f"{l} Label"
        inside_formatter = lambda l, v: f"${v}"

        chart = BarChart(
            data,
            base_label_formatter=base_formatter,
            inside_label_formatter=inside_formatter,
        )

        assert chart._base_label_formatter("A", 10) == "A Label"
        assert chart._inside_label_formatter("A", 10) == "$10"


class TestBarChartDataValidation:
    """Test data validation and edge cases."""

    def test_negative_values_raise_error(self):
        with pytest.raises(
            ValueError, match="Negative values are not currently supported"
        ):
            BarChart({"A": 10, "B": -5})

    def test_all_zero_values(self):
        chart = BarChart({"A": 0, "B": 0})
        assert chart._calculate_scale() == 1

    def test_mixed_int_float_values(self, extended_data):
        extended_data["B"] = 20.5
        chart = BarChart(extended_data)
        assert chart.data == extended_data

    @pytest.mark.parametrize(
        "data,expected_max",
        [
            ({"A": 1000000, "B": 2000000}, 2000000),
            ({"A": 0.001, "B": 0.002}, 0.002),
        ],
    )
    def test_extreme_values(self, data, expected_max):
        chart = BarChart(data)
        scale = chart._calculate_scale()
        assert scale == chart._max_bar_height / expected_max


class TestBarChartUpdateData:
    """Test data update functionality."""

    def test_update_data_basic(self, basic_chart):
        new_data = {"X": 15, "Y": 25, "Z": 30}
        basic_chart.update_data(new_data)

        assert basic_chart.data == new_data
        assert len(basic_chart) == 3

    @pytest.mark.parametrize(
        "invalid_data,error_type,error_msg",
        [
            ({}, ValueError, "Data cannot be empty"),
            ([("X", 20)], TypeError, "Data must be a dict"),
            ({"X": "invalid"}, TypeError, "must be numeric"),
        ],
    )
    def test_update_data_invalid(
        self, basic_chart, invalid_data, error_type, error_msg
    ):
        with pytest.raises(error_type, match=error_msg):
            basic_chart.update_data(invalid_data)

    def test_update_data_adjusts_colors(self):
        chart = BarChart({"A": 10, "B": 20}, bar_colors=["#ff0000", "#00ff00"])
        chart.update_data({"X": 5, "Y": 10, "Z": 15})
        assert len(chart._bar_colors) == 3


class TestBarChartUpdateColors:
    """Test color update functionality."""

    @pytest.mark.parametrize(
        "colors,expected",
        [
            ("#ff0000", ["#ff0000", "#ff0000"]),
            (["#ff0000", "#00ff00"], ["#ff0000", "#00ff00"]),
        ],
    )
    def test_update_colors(self, basic_chart, colors, expected):
        basic_chart.update_colors(colors)
        assert basic_chart._bar_colors == expected

    def test_update_colors_preserves_original(self):
        chart = BarChart({"A": 10, "B": 20}, bar_colors=["#ff0000"])
        chart.update_data({"A": 10, "B": 20, "C": 30})
        assert all(c == "#ff0000" for c in chart._bar_colors)


class TestBarChartMove:
    """Test chart repositioning."""

    @pytest.mark.parametrize(
        "start_pos,new_pos",
        [
            ((0, 0), (100, 200)),
            ((100, 100), (-50, -50)),
        ],
    )
    def test_move_basic(self, start_pos, new_pos):
        chart = BarChart({"A": 10}, position=start_pos)
        chart.move(new_pos)
        assert chart.position == new_pos

    @pytest.mark.parametrize("invalid_pos", [(100,), 100])
    def test_move_invalid_position(self, basic_chart, invalid_pos):
        with pytest.raises(ValueError, match="must be a tuple of"):
            basic_chart.move(invalid_pos)

    def test_move_updates_all_objects(self):
        chart = BarChart({"A": 10, "B": 20}, position=(0, 0))
        initial_positions = [obj.position for obj in chart.group.objects]

        chart.move((50, 100))

        for initial, obj in zip(initial_positions, chart.group.objects):
            new_pos = obj.position
            assert new_pos[0] == initial[0] + 50
            assert new_pos[1] == initial[1] + 100


class TestBarChartAxisAndTicks:
    """Test axis and tick functionality."""

    def test_axis_disabled_by_default(self, basic_chart):
        assert basic_chart._show_axis is False

    @pytest.mark.parametrize(
        "show_axis,tick_count",
        [
            (True, None),
            (True, 10),
            (True, 0),
        ],
    )
    def test_axis_configuration(self, show_axis, tick_count):
        kwargs = {"show_axis": show_axis}
        if tick_count is not None:
            kwargs["axis_tick_count"] = tick_count

        chart = BarChart({"A": 10}, **kwargs)
        assert chart._show_axis == show_axis
        if tick_count is not None:
            assert chart._axis_tick_count == tick_count


class TestBarChartDimensions:
    """Test dimension calculations."""

    def test_calculate_chart_dimensions_basic(self):
        chart = BarChart(
            {"A": 10, "B": 20, "C": 15},
            bar_width=40,
            bar_spacing=20,
            max_bar_height=200,
        )
        width, _height = chart._calculate_chart_dimensions()
        expected_width = 3 * 40 + 2 * 20
        assert width == expected_width

    def test_calculate_chart_dimensions_with_title(self):
        chart = BarChart(
            {"A": 10}, title="Test", title_text_format=TextFormat(fontSize=20)
        )
        _width, height = chart._calculate_chart_dimensions()
        assert height > chart._max_bar_height

    def test_calculate_chart_dimensions_single_bar(self):
        chart = BarChart({"A": 10}, bar_width=50)
        width, _height = chart._calculate_chart_dimensions()
        assert width == 50


class TestBarChartScaleCalculation:
    """Test scale calculation for bar heights."""

    @pytest.mark.parametrize(
        "data,max_height,expected_scale",
        [
            ({"A": 50, "B": 100}, 200, 2.0),
            ({"A": 50, "B": 50, "C": 50}, 200, 4.0),
            ({"A": 25}, 100, 4.0),
        ],
    )
    def test_calculate_scale(self, data, max_height, expected_scale):
        chart = BarChart(data, max_bar_height=max_height)
        assert chart._calculate_scale() == expected_scale


class TestBarChartTextFormatting:
    """Test text formatting and label formatters."""

    def test_custom_text_formats(self):
        title_fmt = TextFormat(fontSize=24, align="left")
        base_fmt = TextFormat(fontSize=10, color="#ff0000")

        chart = BarChart(
            {"A": 10},
            title="Test",
            title_text_format=title_fmt,
            base_text_format=base_fmt,
        )

        assert chart._title_text_format.fontSize == 24
        assert chart._base_text_format.fontSize == 10

    @pytest.mark.parametrize(
        "label,value,formatter,expected",
        [
            ("A", 10.5, lambda l, _v: f"[{l}]", "[A]"),
            ("A", 10.5, lambda _l, v: f"${v:.2f}", "$10.50"),
        ],
    )
    def test_label_formatter(self, label, value, formatter, expected):
        assert formatter(label, value) == expected


class TestBarChartBackgroundAndStyling:
    """Test background and styling options."""

    @pytest.mark.parametrize(
        "param,value,attr",
        [
            ("background_color", "#f0f0f0", "_background_color"),
            ("bar_stroke_color", "#ff0000", "_bar_stroke_color"),
        ],
    )
    def test_styling_params(self, param, value, attr):
        chart = BarChart({"A": 10}, **{param: value})
        assert getattr(chart, attr) == value

    def test_bar_fill_color_override(self):
        chart = BarChart(
            {"A": 10, "B": 20},
            bar_colors=["#ff0000", "#00ff00"],
            bar_fill_color="#0000ff",
        )
        assert chart._bar_fill_color == "#0000ff"


class TestBarChartGroupIntegration:
    """Test integration with Group object."""

    def test_group_contains_objects(self, basic_chart):
        assert len(basic_chart.group.objects) > 0

    def test_add_to_page(self, basic_chart):
        mock_page = Mock()
        basic_chart.add_to_page(mock_page)
        assert mock_page.add_object.call_count == len(basic_chart.group.objects)


class TestBarChartRepr:
    """Test string representation."""

    def test_repr(self):
        chart = BarChart({"A": 10, "B": 20}, position=(50, 100))
        repr_str = repr(chart)

        assert all(s in repr_str for s in ["BarChart", "bars=2", "(50, 100)"])

    def test_len(self, extended_data):
        chart = BarChart(extended_data)
        assert len(chart) == 3


class TestBarChartEdgeCases:
    """Test various edge cases and boundary conditions."""

    @pytest.mark.parametrize(
        "data,expected_len",
        [
            ({"A": 100}, 1),
            ({f"Bar{i}": i * 10 for i in range(50)}, 50),
        ],
    )
    def test_chart_size_variations(self, data, expected_len):
        chart = BarChart(data)
        assert len(chart) == expected_len

    @pytest.mark.parametrize(
        "data",
        [
            {"A & B": 10, "C/D": 20, "E-F": 15},
            {"café": 10, "naïve": 20, "日本": 15},
            {"": 10, "B": 20},
        ],
    )
    def test_label_variations(self, data):
        chart = BarChart(data)
        assert chart.data == data

    def test_multiple_updates(self):
        chart = BarChart({"A": 10})

        chart.update_data({"B": 20, "C": 30})
        assert len(chart) == 2

        chart.update_colors(["#ff0000", "#00ff00"])
        assert chart._bar_colors == ["#ff0000", "#00ff00"]

        chart.move((100, 100))
        assert chart.position == (100, 100)

    def test_data_property_returns_copy(self):
        chart = BarChart({"A": 10})
        data = chart.data
        data["B"] = 20

        assert "B" not in chart.data
        assert chart.data == {"A": 10}
