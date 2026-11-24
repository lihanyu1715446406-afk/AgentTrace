"""文本切分：把长文档切成带重叠的 chunk。"""

from __future__ import annotations


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """把长文本切分为若干 chunk（优先按空行分段落聚合，超长段落硬切）。

    - ``chunk_size``：单个 chunk 的目标最大字符数。
    - ``chunk_overlap``：相邻 chunk 重叠的字符数，用于减少语义在边界被切断。
    """
    if chunk_size < 1:
        raise ValueError("chunk_size 必须 >= 1")
    chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    # 优先按空行分段落；无空行时退化为整体。
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            chunks.append(buf)
            buf = ""

    for para in paragraphs:
        # 单段超长：硬切成窗口，保留 overlap。
        while len(para) > chunk_size:
            flush()
            chunks.append(para[:chunk_size])
            para = para[chunk_size - chunk_overlap :]
        # 合并进当前缓冲；放不下则先冲掉缓冲再起新段。
        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            flush()
            buf = para
    flush()
    return chunks
