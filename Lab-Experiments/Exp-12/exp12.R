diabetes <- read.csv("diabetes.csv")
A <- c(diabetes$Age)

Mean <- mean(A)
Std <- sd(A)
print(paste("Mean =", round(Mean, 4)))
print(paste("Standard deviation =", round(Std, 4)))

Zscore <- (A - Mean) / Std
print("First 10 Z-scores:")
print(round(head(Zscore, 10), 4))

# Check: mean of Z-scores = 0 and standard deviation = 1
print(round(mean(Zscore), 4))
print(round(sd(Zscore), 4))
