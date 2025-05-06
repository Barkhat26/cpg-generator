<%@ taglib prefix="s" uri="/struts-tags" %>
<html>
<head><title>Struts2 Example</title></head>
<body>
  <h2>Enter Your Name</h2>
  <s:form action="hello">
    <s:textfield name="name" label="Name"/>
    <s:submit value="Say Hello"/>
  </s:form>
</body>
</html>
