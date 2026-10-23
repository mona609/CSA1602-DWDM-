diabetes <- read.csv("diabetes.csv")
A <- c(diabetes$Age)

# MEAN
Mean <- mean(A)
print(paste("Mean    =", round(Mean, 4)))

# MINIMUM
Minimum <- min(A)
print(paste("Minimum =", Minimum))

# MAXIMUM
Maximum <- max(A)
print(paste("Maximum =", Maximum))

# MIN-MAX NORMALIZATION
MinMax <- (A - Minimum) / (Maximum - Minimum)
print("First 10 min-max normalized values:")
print(round(head(MinMax, 10), 4))
