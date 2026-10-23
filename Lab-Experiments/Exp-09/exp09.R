name <- c("siri", "mahi", "chiru")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

q1 <- quantile(df$age, 0.25)
q3 <- quantile(df$age, 0.75)
print(paste("Q1 =", q1))
print(paste("Q3 =", q3))

print(IQR(df$age))

write.csv(df, "datafr.csv")
