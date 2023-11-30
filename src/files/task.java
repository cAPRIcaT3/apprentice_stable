// SpecializedTask.java

import java.util.Scanner;

public class SpecializedTask {

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter a string: ");
        String inputString = scanner.nextLine();

        int stringLength = calculateStringLength(inputString);
        System.out.println("Length of the entered string: " + stringLength);

        scanner.close();
    }

    private static int calculateStringLength(String str) {
        return str.length();
    }
}
