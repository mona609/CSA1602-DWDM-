name <- c("siri", "mahi", "chiru")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

# Quartiles
print(quantile(df$age))

# Any other quantiles
print(quantile(df$age, probs = c(0.10, 0.90)))

write.csv(df, "datafr.csv")
