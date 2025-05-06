from web_driver import WebDriver

projectConfig = {
    "DB": r"F:\tmp\dvja-analysis\dvja-analysis.db",
    "REPO": r"F:\tmp\dvja\.git",
    "SAVED_BRANCH_FILE": "saved_branch.txt",
    "JSPFilesDir": r"F:\tmp\dvja\src\main\webapp\WEB-INF",
    "STRUTS_XML": r"F:\tmp\dvja\src\main\resources\struts.xml",
    "VIEWS_DIR": "",
    "base_url": "http://localhost:8080",
    "auth_login": "khbr",
    "auth_password": "password1337"
}


class DVJADriver(WebDriver):
    def authenticate(self):
        payload = {
            "login": projectConfig["auth_login"],
            "password": projectConfig["auth_password"]
        }
        base_url = projectConfig["base_url"]
        self.s.post(f"{base_url}/login", data=payload)
