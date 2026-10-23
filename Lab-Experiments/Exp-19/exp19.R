diabetes <- read.csv("diabetes.csv")

# Linear regression: BloodPressure depends on Age
Relation <- lm(BloodPressure ~ Age, data = diabetes)

print(Relation)
print(summary(Relation))

# Plot with the regression line
plot(diabetes$Age, diabetes$BloodPressure, col = "green",
     main = "Linear Regression Analysis",
     xlab = "Age", ylab = "BloodPressure", pch = 19)
abline(Relation, col = "red", lwd = 2)

# Predict the blood pressure of a patient aged 50
new_patient <- data.frame(Age = 50)
print(predict(Relation, new_patient))
