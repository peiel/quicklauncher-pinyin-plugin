# QuickLauncher 拼音注音

输入文字或使用其他应用中选中的文字，输出带声调的汉语拼音。转换在本机完成，不联网、不读取剪贴板；QuickLauncher 执行成功后会显示并复制结果。

## 安装

1. 打开 QuickLauncher 的「设置 → 插件 → 发现」，选择「导入插件」，选择本 `quicklauncher-pinyin` 目录。
2. 检查插件代码与附带依赖并确认导入。如果应用没有自动启用，请在插件设置中启用它。
3. 本插件需要 Python 3；若无法运行，请在 QuickLauncher 插件设置中检查 Python 解释器。拼音依赖已经包含在插件中，无需 `pip install`。

导入时 QuickLauncher 会复制文件：之后修改此目录不会自动更新已安装的副本。重新导入相同 ID 前需要移除旧副本，注意保留用户设置。

## 使用

- **输入文字**：在 QuickLauncher 中输入 `py 你好`，选中「拼音注音」并按回车，得到并复制 `nǐ hǎo`。
- **选中文字**：在其他应用中选中文字，打开 QuickLauncher，输入 `py`，选中「拼音注音」并按回车。
- 如无法读取选区，在「系统设置 → 隐私与安全性 → 辅助功能」中检查是否允许 QuickLauncher，并确认目标应用支持暴露选中文本；安全输入控件不支持。若无选区或无法读取，请改用 `py 中文`。

使用普通触发而非关键词即时预览：QuickLauncher 的即时预览不会读取其他应用的选区。插件使用词组字典尽量处理多音字；姓名、歧义词及生僻字可能需要人工核对，不认识的字符原样保留。非中文文本与标点保留，拼音之间及必要的中英文边界插入空格。

QuickLauncher 限制输入最多 1024 UTF-8 字节，`copyAndShow` 输出最多 200 字符且不能含换行或控制字符；过长或多行文本请分段处理。插件不会静默截断结果。

## 测试

```sh
python3 -m unittest discover -s tests -v
printf '%s\n' '{"version":1,"arguments":"你好"}' | python3 main.py
```

这两种方式仅模拟脚本协议，不证明 QuickLauncher 的选区获取、界面或剪贴板行为；这些需要在应用里单独验证。

## 第三方依赖

本插件内置 [pypinyin 0.55.0](https://github.com/mozillazg/python-pinyin)，包括来自 [pinyin-data](https://github.com/mozillazg/pinyin-data) 和 [phrase-pinyin-data](https://github.com/mozillazg/phrase-pinyin-data) 的字典。各项目采用 MIT 许可证；版权声明和许可证分别位于 `vendor/pypinyin/LICENSE.txt`、`LICENSE-pinyin-data.txt` 和 `LICENSE-phrase-pinyin-data.txt`。
