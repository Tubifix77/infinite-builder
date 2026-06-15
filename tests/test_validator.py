from builder.validator import validate

GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1>
<script>console.log('hi');</script>
</body></html>"""

def test_good_html_passes():
    ok, reason = validate(GOOD_HTML)
    assert ok, reason

def test_too_short_fails():
    ok, reason = validate("<html><script>x</script></html>")
    assert not ok

def test_missing_script_fails():
    ok, reason = validate("<!DOCTYPE html><html><body><p>hi</p></body></html>")
    assert not ok

def test_truncated_fails():
    ok, reason = validate("<html><script>console.log('hi')</script>")
    assert not ok

def test_refusal_detected():
    ok, reason = validate("I cannot create this application because...")
    assert not ok

def test_empty_fails():
    ok, reason = validate("")
    assert not ok

def test_js_operators_dont_fail():
    # => >= <= comparisons and template literals contain < > but are valid
    html = """<!DOCTYPE html><html><head></head><body>
<script>
const fn = (x) => x >= 10 ? 'big' : 'small';
const items = [1,2,3].filter(n => n > 1).map(n => `<li>${n}</li>`);
</script></body></html>"""
    ok, reason = validate(html)
    assert ok, reason
