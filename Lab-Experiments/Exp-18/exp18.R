set.seed(9)
x <- rnorm(1000)
y <- rnorm(1000)

# Ordinary scatter plot
plot(x, y, main = "Scatter Plot", xlab = "x", ylab = "y", pch = 20, col = "blue")

# Smooth scatter plot (shows where the points are dense)
smoothScatter(x, y, main = "Smooth Scatter Plot", xlab = "x", ylab = "y")
