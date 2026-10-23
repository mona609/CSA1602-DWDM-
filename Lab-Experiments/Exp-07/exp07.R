# Summary
name <- c("siri", "mahi", "chiru")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

print(summary(df$age))

print(summary(df))

write.csv(df, "datafr.csv")
