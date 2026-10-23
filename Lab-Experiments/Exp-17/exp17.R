diabetes <- read.csv("diabetes.csv")

# Pearson correlation between Age and Insulin
print(cor(diabetes$Age, diabetes$Insulin))

# Is the correlation significant?
print(cor.test(diabetes$Age, diabetes$Insulin))

# Correlation matrix
print(round(cor(diabetes[, c("Age", "BloodPressure", "Glucose", "Insulin")]), 3))

# Chi-square test of independence between age group and insulin group
age_group <- cut(diabetes$Age, breaks = c(20, 30, 40, 100),
                 labels = c("21-30", "31-40", "Above 40"))
insulin_group <- cut(diabetes$Insulin, breaks = c(-1, 50, 100, 1000),
                     labels = c("Low", "Medium", "High"))
tbl <- table(age_group, insulin_group)
print(tbl)
print(chisq.test(tbl))
