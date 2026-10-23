name <- c("siri", "mahi", "chiru")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

r <- range(df$age)
print(r)

print(paste("Range     =", r[2] - r[1]))
print(paste("Mid range =", (r[1] + r[2]) / 2))

write.csv(df, "datafr.csv")
