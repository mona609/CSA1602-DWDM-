diabetes <- read.csv("diabetes.csv")

input <- diabetes[, c("Age", "BloodPressure", "Glucose")]

# Multiple regression model
model <- lm(Age ~ BloodPressure + Glucose, data = input)
print(model)

# Intercept and coefficients
a <- coef(model)[1]
xBloodPressure <- coef(model)[2]
yGlucose <- coef(model)[3]
print(a)
print(xBloodPressure)
print(yGlucose)

# Equation: Age = a + xBloodPressure * BloodPressure + yGlucose * Glucose
cat("Age =", round(a, 4), "+", round(xBloodPressure, 4), "* BloodPressure +",
    round(yGlucose, 4), "* Glucose\n")

# Prediction for BloodPressure = 80 and Glucose = 120
y <- a + xBloodPressure * 80 + yGlucose * 120
print(unname(y))
