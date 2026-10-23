num1 <- as.integer(readline(prompt = "Enter the first number: "))
num2 <- as.integer(readline(prompt = "Enter the second number: "))

if (num2 == 0) {
  print("Division by zero is not possible")
} else {
  num3 <- num1 / num2
  print(num3)
}
