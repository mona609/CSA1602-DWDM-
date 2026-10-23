a <- c(55, 67, 89, 80, 90)

# Bar plot
barplot(a, names.arg = c("A", "B", "C", "D", "E"),
        main = "Bar Plot", xlab = "Category", ylab = "Value",
        col = "steelblue")

# Horizontal bar plot
barplot(a, names.arg = c("A", "B", "C", "D", "E"), horiz = TRUE,
        main = "Horizontal Bar Plot", xlab = "Value", ylab = "Category",
        col = "orange")
