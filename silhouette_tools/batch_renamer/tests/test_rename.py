from unittest.mock import MagicMock

from bfs_renamer.renamer.renamer import LayerRenamer
from fx import Layer, Shape


def make_mock_layer(label, children=None):
    mock = MagicMock(spec=Layer)
    mock.label = label
    mock.children = children or []
    return mock


def make_mock_shape(label):
    mock = MagicMock(spec=Shape)
    mock.label = label
    return mock


def test_renames_shapes_correctly():
    shape1 = make_mock_shape("old1")
    shape2 = make_mock_shape("old2")
    layer = make_mock_layer("Body", children=[shape1, shape2])

    renamer = LayerRenamer(base_label="Body")
    renamer.rename(layer)

    assert shape1.label == "Body001"
    assert shape2.label == "Body002"


def test_renames_sub_layers_correctly():
    sub_layer = make_mock_layer("old_sub", children=[])
    layer = make_mock_layer("Body", children=[sub_layer])

    renamer = LayerRenamer(base_label="Body")
    renamer.rename(layer)

    assert sub_layer.label == "Body001"


def test_total_counts_are_correct():
    shape1 = make_mock_shape("s1")
    shape2 = make_mock_shape("s2")
    sub_layer = make_mock_layer("sub", children=[shape1, shape2])
    layer = make_mock_layer("Body", children=[sub_layer])

    renamer = LayerRenamer(base_label="Body")
    renamer.rename(layer)

    assert renamer.total_layers_renamed == 1
    assert renamer.total_shapes_renamed == 2
