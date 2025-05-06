public class Zoo {
    public static void main(String[] args) {
        Animal lion = new Lion("Симба");
        Animal elephant = new Elephant("Дамбо");

        lion.makeSound();       // Симба рычит!
        elephant.makeSound();   // Дамбо трубит!
    }
}
