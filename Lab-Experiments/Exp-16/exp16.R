a <- c(55, 67, 89, 80, 90)

h <- hist(a, main = "Histogram of a", xlab = "a", ylab = "Frequency",
          col = "lightgreen", border = "black")

# Number of values in each bin
print(h$breaks)
print(h$counts)
