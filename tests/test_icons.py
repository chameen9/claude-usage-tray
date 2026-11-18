from claude_usage_tray import icons


def px(img, x, y):
    return img.getpixel((x, y))


def test_ring_size_and_transparent_centre():
    img = icons.ring_icon(50)
    assert img.size == (64, 64)
    assert px(img, 32, 32)[3] == 0


def test_ring_fill_direction_and_colour():
    img = icons.ring_icon(25)  # clockwise from 12 o'clock -> top-right quadrant filled
    r, g, b, a = px(img, 50, 10)
    assert a > 200 and g > r  # green arc
    r, g, b, a = px(img, 14, 50)  # bottom-left only has the grey track
    assert abs(r - g) < 10


def test_colour_thresholds():
    assert icons.color_for(69, False) == icons.GREEN
    assert icons.color_for(70, False) == icons.YELLOW
    assert icons.color_for(90, False) == icons.RED
    assert icons.color_for(95, True) == icons.GREY
    assert icons.color_for(None, False) == icons.GREY


def test_combined_icon_renders():
    assert icons.combined_icon(20, False, 80, False).size == (64, 64)
