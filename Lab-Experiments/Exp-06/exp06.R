# Mean, Median and Mode
name <- c("siri", "mahi", "chiru")
age <- c(23, 24, 35)
marks <- c(88, 78, 25)
df <- data.frame(name, age, marks)

# MEAN
print(mean(df$age))

# MEDIAN
print(median(df$age))

# MODE
# R has no built-in function for the statistical mode
# (mode() only returns the data type), so we write our own function
get_mode <- function(x) {
  counts <- table(x)
  as.numeric(names(counts)[counts == max(counts)])
}
scores <- c(88, 78, 25, 88, 90, 88)
print(get_mode(scores))

write.csv(df, "datafr.csv")
