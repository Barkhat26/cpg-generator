<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<html>
<head>
    <title>Форма</title>
</head>
<body>
    <h2>Введите ваше имя:</h2>
    <form action="form" method="post">
        <input type="text" name="name" placeholder="Ваше имя" required />
        <button type="submit">Отправить</button>
    </form>
</body>
</html>