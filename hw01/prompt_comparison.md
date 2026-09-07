Strategy 1: "How should a BI analyst communicate data limitations to a non-technical audience?"
"Good communication about data limitations comes down to translating technical caveats into business impact — what someone might get wrong if they don't know about the gap, not the mechanics of why the gap exists. A few principles that hold up well in practice, and I'll tie them to a dataset like this loan portfolio file to make them concrete:

Lead with the decision, not the flaw. Instead of "the credit score field has 4% missing values," say "for about 1 in 25 loans, we can't verify creditworthiness — so the default-rate-by-credit-score chart understates risk in that segment slightly." Non-technical stakeholders act on decisions, not data quality metrics, so frame the limitation as "here's what this means for what you're about to decide."

Put it where the eyes are, not in a footnote nobody reads. A caveat buried in an appendix might as well not exist."

This strategy did well at answering the question simply. However, it was missing more context and the role it was supposed to play. This approach would be good for a simple quick answer

Strategy 2: You are a consultant communicating to the BI analyst team on how to best communicate. Answer the question "How should a BI analyst communicate data limitations to a non-technical audience?"
"A few honest data limitations in this file are actually a good backbone for the memo, so I pulled them before drafting general advice.

Communicating data limitations well comes down to one shift in mindset: stop treating limitations as a disclaimer you bolt onto the end of a report, and start treating them as part of the answer to the business question. A non-technical stakeholder doesn't need to understand why a limitation exists — they need to know what it means for the decision they're about to make. That reframe drives everything else.

Translate the limitation into a decision consequence, not a statistical concept. Don't say "the sample has selection bias" — say "these numbers only reflect approved loans, so they'll make our risk look better than it really is, because rejected applicants aren't in here." Don't say "there's a censoring issue in the outcome variable" — say "6 in 10 of these loans are still active, so we don't yet know how many will eventually default; the true default rate will end up higher than what you're seeing today." 
The technical term can appear in parentheses for the record, but the sentence has to work without it."

This time, Claude did a much better job of playing specific role and speaking to this audience. It supported what it said with real numbers and answered more specifically

Strategy 3: "How should a BI analyst communicate data limitations to a non-technical audience?" Here is an example of how I want the response: "Answer,

Evidence 1

Evidence 2

Conclusion"

"Answer: A BI analyst should communicate data limitations to a non-technical audience by translating technical caveats into plain-language statements about confidence and scope, embedding them directly alongside the relevant numbers or visuals rather than burying them in a footnote or appendix, and framing them in terms of what decisions the data can and cannot safely support.

Evidence 1: Limitations framed in technical terms (sample size, confidence intervals, data latency, missing values) are often skipped over or misunderstood by non-technical stakeholders, but the same limitations translated into business language ("this trend is based on three weeks of data, so it may shift as more comes in" or "this figure excludes about 15% of transactions that couldn't be matched") are far more likely to be understood and remembered, because they connect directly to the decision being made rather than to statistical mechanics the audience doesn't need to evaluate.

This approach did a much better job of giving me the answer in the format I wanted it. This would be very good in situations where I need a specific format.

Conclusion: Each of the three strategies used had their advantages. The first strategy was the easiest, didn't take a lot of extra planning, and still gave the answer I wanted.
The second approach gave a much more sophisticated answer and spoke to me like I was apart of a BI analyst team. The third strategy was easiest for me to read, since it was in my desired format.
Overall, the second approach gave the most useful output, because it catered most to what I needed. It would be the most effective in helping a BI analyst communicate to others
