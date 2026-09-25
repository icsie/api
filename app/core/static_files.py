"""限制公開靜態檔案類型的 StaticFiles 實作。"""

import stat
from pathlib import Path

from starlette.staticfiles import StaticFiles


class HtmlCssOnlyStaticFiles(StaticFiles):
    """只提供允許的前端靜態資源，拒絕其他公開檔案類型。

    目錄本身仍會交給 Starlette 處理，這樣根目錄可以透過 html=True
    找到 index.html；實際檔案則必須符合副檔名或目錄白名單。
    """

    allowed_extensions = {".css", ".html", ".svg"}
    allowed_directories = {"js", "json"}

    def lookup_path(self, path: str):
        """查找檔案，並在回傳前拒絕非 HTML/CSS 的一般檔案。"""

        full_path, stat_result = super().lookup_path(path)

        # 目錄要保留，因為 StaticFiles 需要用它尋找 index.html。
        if stat_result is None or not stat.S_ISREG(stat_result.st_mode):
            return full_path, stat_result

        # js/ 與 json/ 目錄內的檔案可提供，不限制其副檔名。
        path_parts = Path(path).parts
        is_allowed_directory = bool(path_parts) and path_parts[0].lower() in self.allowed_directories

        # 其他位置只允許 HTML、CSS、SVG，副檔名不分大小寫。
        is_allowed_extension = Path(path).suffix.lower() in self.allowed_extensions
        if not is_allowed_directory and not is_allowed_extension:
            return "", None

        return full_path, stat_result