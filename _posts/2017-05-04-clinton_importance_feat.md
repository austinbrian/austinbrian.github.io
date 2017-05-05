---
layout: post
title: "The most important factor in the 2016 election? Student loans."
author: "Brian Austin"
meta: "politics, presidential election, 2016, taxes"
---
If you took all 3,113 counties in the United States, and wanted to try and guess whether a county would cast more votes for Hillary Clinton or Donald Trump, the most important pieces of information to have be the number of people who claim an education-related deduction or credit.

This finding on student loans is part of my ongoing analysis of the intersection of 2016 voting behavior and tax return information.

<details><summary>More methodology</summary>
This analysis was performed using a random forest classifier, which used 124 variables drawn from county-level 2014 IRS data. Variables included aggregate totals and participant counts for each income type and deduction. The dataset was matched by county with the New York *Times* report of election night votes. Average cross-validated accuracy score using the model's classification was approximately 0.89 (*good!*) and an F1 score of 0.88 (*not bad!*).
</details>
<br>
To be sure, these groups of voters are qualitatively different in other measurable ways. For instance, the number of farm returns in a county is the next-most impactful feature in the income dataset behind education credits and deductions. Counties with the highest numbers of these returns were the most likely in the data to cast more returns for Trump than Clinton.

But these findings largely conform to the behaviors we might expect of the electorate. Those with higher levels of education (especially those at high-cost liberal arts colleges) are most likely to inhabit counties that vote for Clinton. Farmers were more likely to vote Trump.

Perhaps more interesting are the distinctions that weren't found in the dataset. Most importantly, total taxable income did not emerge as an especially valuable predictor.
<br>

![](../images/agi_pp_vs_clinton.png)
<br>

The figure above demonstrates the distribution of income, as separated by Clinton's margin over Trump (or vice versa). Each blue dot represents a county in which more people voted for Clinton than Trump, and each red dot shows a county with more Trump votes.

While the sheer numbers for the Trump voters are significantly greater - Trump won about 84 percent of US counties - the distribution of incomes is relatively similar between them.
