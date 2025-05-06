class Report:
    def addRecord(self, attackEndpoint, testParam):
        # TODO:
        ...

    def dump(self):
        # TODO:
        example_data = {
            "XSS": [
                {
                    "uri": "/addEditProduct",
                    "param": "product.name",
                    "line": 86,
                    "file": "F:\\tmp\\dvja\\src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                    "code": "productService.save(product);"
                },
                {
                    "uri": "/addEditProduct",
                    "param": "product.code",
                    "line": 86,
                    "file": "F:\\tmp\\dvja\\src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                    "code": "productService.save(product);"
                }
            ]
        }
        ...