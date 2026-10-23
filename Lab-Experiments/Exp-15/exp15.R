name <- c("siri", "chiru", "loki")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

# Five-number summary: min, Q1, median, Q3, max
print(fivenum(df$age))

# Box plot
boxplot(df$age, main = "Box Plot of Age", ylab = "Age", col = "lightblue")
