package cpganalyzer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.logging.Logger;
import java.util.logging.Level;

public class CheckPointSaver {

    private final File directory;
    private static final Logger logger = Logger.getLogger(CheckPointSaver.class.getName());

    public CheckPointSaver(String directoryPath) {
        this.directory = new File(directoryPath);

        if (!directory.exists()) {
            if (directory.mkdirs()) {
                logger.info("Directory created: " + directory.getAbsolutePath());
            } else {
                logger.severe("Failed to create directory: " + directory.getAbsolutePath());
            }
        }
    }

    public void saveToFile(String name, Object value) {
        if (!isValidFilename(name)) {
            logger.warning("Invalid filename: " + name);
            return;
        }

        File file = new File(directory, name + ".txt");

        try (FileWriter writer = new FileWriter(file)) {
            writer.write(String.valueOf(value));
            logger.info("File saved successfully: " + file.getAbsolutePath());
        } catch (IOException e) {
            logger.log(Level.SEVERE, "Error writing to file: " + file.getAbsolutePath(), e);
        }
    }

    private boolean isValidFilename(String name) {
        // Basic check for invalid characters in file names
        return name != null && !name.matches(".*[\\\\/:*?\"<>|].*");
    }
}
