"""限制公開靜態檔案類型的 StaticFiles 實作。"""

import stat
from pathlib import Path

from starlette.staticfiles import StaticFiles


class HtmlCssOnlyStaticFiles(StaticFiles):
    """只提供 HTML 與 CSS 檔案，拒絕其他公開檔案類型。

    目錄本身仍會交給 Starlette 處理，這樣根目錄可以透過 html=True
    找到 index.html；只有實際要回傳的檔案會受到副檔名白名單限制。
    """

    allowed_extensions = {".html", ".css"}

    def lookup_path(self, path: str):
        """查找檔案，並在回傳前拒絕非 HTML/CSS 的一般檔案。"""

        full_path, stat_result = super().lookup_path(path)

        # 目錄要保留，因為 StaticFiles 需要用它尋找 index.html。
        if stat_result is None or not stat.S_ISREG(stat_result.st_mode):
            return full_path, stat_result

        # 副檔名使用小寫比較，讓 .HTML 與 .CSS 也能正常使用。
        if Path(path).suffix.lower() not in self.allowed_extensions:
            return "", None

        return full_path, stat_result