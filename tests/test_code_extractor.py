"""Tests for code extractor."""
import pytest
from src.parser.code_extractor import CodeExtractor


def test_extract_python_code():
    """Test extracting Python code blocks."""
    text = """
Here's a Python function:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

This calculates factorial.
"""
    
    blocks = CodeExtractor.extract_code_blocks(text)
    
    assert len(blocks) == 1
    assert blocks[0].language == 'python'
    assert 'def factorial' in blocks[0].code
    assert blocks[0].line_start > 0


def test_extract_javascript_code():
    """Test extracting JavaScript code blocks."""
    text = """
```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```
"""
    
    blocks = CodeExtractor.extract_code_blocks(text)
    
    assert len(blocks) == 1
    assert blocks[0].language == 'javascript'
    assert 'function greet' in blocks[0].code


def test_extract_multiple_blocks():
    """Test extracting multiple code blocks."""
    text = """
First:
```python
print("Hello")
```

Second:
```javascript
console.log("World");
```
"""
    
    blocks = CodeExtractor.extract_code_blocks(text)
    
    assert len(blocks) == 2
    assert blocks[0].language == 'python'
    assert blocks[1].language == 'javascript'


def test_language_normalization():
    """Test language name normalization."""
    text = """
```py
print("test")
```

```js
console.log("test");
```
"""
    
    blocks = CodeExtractor.extract_code_blocks(text)
    
    assert blocks[0].language == 'python'
    assert blocks[1].language == 'javascript'


def test_filter_executable():
    """Test filtering executable code blocks."""
    from src.models.response import CodeBlock
    
    blocks = [
        CodeBlock(language='python', code='print("test")'),
        CodeBlock(language='markdown', code='# Header'),
        CodeBlock(language='javascript', code='console.log("test")'),
        CodeBlock(language='unknown', code='test')
    ]
    
    executable = CodeExtractor.filter_executable_blocks(blocks)
    
    assert len(executable) == 2
    assert all(b.language in ['python', 'javascript'] for b in executable)


def test_validate_python_syntax():
    """Test Python syntax validation."""
    from src.models.response import CodeBlock
    
    # Valid code
    valid_block = CodeBlock(language='python', code='print("hello")')
    is_valid, error = CodeExtractor.validate_syntax(valid_block)
    assert is_valid
    assert error == ""
    
    # Invalid code
    invalid_block = CodeBlock(language='python', code='print("unclosed')
    is_valid, error = CodeExtractor.validate_syntax(invalid_block)
    assert not is_valid
    assert 'syntax error' in error.lower()


def test_no_code_blocks():
    """Test when no code blocks are present."""
    text = "This is just plain text with no code."
    
    blocks = CodeExtractor.extract_code_blocks(text)
    
    assert len(blocks) == 0
