# text_norm

本目录用于存放各语言的text_norm脚本。

## 命名规则

- **文件名必须使用三字母全大写代码（如 ARE、JPN、KOR）**

- 每个文件对应一种语言的文本规范化逻辑

- 示例：IRQ.py


## 编写要求

每个语言文件必须实现以下函数：

```python
def normalize(text: str) -> str:
    """
    输入：原始文本
    输出：text_norm 后的文本
    """
```

每位负责该语言的同学仅需在文件中完善 normalize()

## 调用方法

```python
from text_norm import get_normalizer

normalize = get_normalizer("ARE")  
text = normalize("示例文本")

```