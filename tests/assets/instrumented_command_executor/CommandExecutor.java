import cpganalyzer.CheckPointSaver;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;

public class CommandExecutor {
    public static void main(String[] args) {
        System.out.print("Введите команду для выполнения: ");
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in))) {
            String command = reader.readLine();

new CheckPointSaver("C:\\Users\\okhabarov\\AppData\\Local\\cpganalyzer\\checkpoints\\command_executor").saveToFile("ch_1", command);
            Process process = Runtime.getRuntime().exec(command);

            // Читаем вывод команды
            BufferedReader stdInput = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader stdError = new BufferedReader(new InputStreamReader(process.getErrorStream()));

            String s;
            System.out.println("Результат выполнения команды:\n");
            while ((s = stdInput.readLine()) != null) {
                System.out.println(s);
            }

            // Ошибки, если есть
            System.out.println("\nОшибки (если есть):\n");
            while ((s = stdError.readLine()) != null) {
                System.out.println(s);
            }

        } catch (IOException e) {
            System.out.println("Произошла ошибка при выполнении команды: " + e.getMessage());
        }
    }
}