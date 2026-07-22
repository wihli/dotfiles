---
name: multi-mind
description: >
  Subagent-based collaborative analysis. Launch 4-6 specialist subagents in parallel
  to analyze a topic from different perspectives, then cross-pollinate and synthesize.
  Usage: /multi-mind <topic> [rounds=3]
---

# Multi-Mind - Subagent-Based Collaborative Analysis

Execute a multi-specialist collaborative analysis using independent subagents.

## Phase 1: Specialist Assignment & Research

Analyze the topic and determine 4-6 specialist roles needed. Then launch parallel subagents using the Task tool with `subagent_type: "general-purpose"`:

**Example specialists** (adapt to topic):
- Technical Specialist: implementation, architecture, performance, technical challenges
- Business Strategy Specialist: market dynamics, competitive landscape, ROI, positioning
- User Experience Specialist: user needs, usability, adoption barriers, human factors
- Risk/Security Specialist: vulnerabilities, failure modes, compliance, mitigation
- Historical/Trends Specialist: precedents, evolution, emerging patterns

**Specialist Selection Criteria**:
- Unique domain expertise relevant to the topic
- Different methodological approaches (quantitative/qualitative, theoretical/practical)
- Varied temporal perspectives (historical, current, future-focused)
- Distinct risk/opportunity sensitivities
- Independent information sources

Each subagent prompt should include:
- Clear specialist role and perspective
- Specific research focus areas
- Instruction to use WebSearch for latest information
- Request for concrete findings, not general observations

## Phase 2: Cross-Pollination Round

After receiving all specialist reports, launch a second round of subagents that:
1. Review all other specialists' findings (pass summaries in prompt)
2. Identify intersections with their domain
3. Challenge assumptions from their perspective
4. Build on insights while maintaining distinct viewpoint
5. Flag blind spots in other analyses

## Phase 3: Synthesis & Iteration

For each round (default 3, user-configurable):
- Collect all subagent outputs
- Synthesize without homogenizing perspectives
- Identify emerging patterns and gaps
- Determine focus areas for next round
- Launch new subagent tasks with refined prompts

## Anti-Repetition Mechanisms

**Moderator Responsibilities** (you, orchestrating):
- Track what has been thoroughly covered vs. needs deeper exploration
- Redirect specialists away from rehashing previous points
- Push for new angles, deeper analysis, broader implications
- Synthesize without homogenizing distinct perspectives

**Specialist Guidelines** (include in prompts):
- Build on previous round insights rather than restating
- Focus on what your unique expertise adds
- Search for information others likely missed
- Challenge emerging consensus from your specialist perspective

## Output Protocol

```
=== MULTI-MIND ANALYSIS: [Topic] ===
Rounds: [X] | Specialists: [List]

--- ROUND 1 ---
KNOWLEDGE ACQUISITION
[Each specialist's web research findings]

SPECIALIST ANALYSIS
[Each specialist's unique perspective]

CROSS-POLLINATION
[Specialists engage with each other's findings]

MODERATOR SYNTHESIS
[Progress assessment, key insights, next round focus]

--- ROUND N ---
[Repeat with deeper analysis building on previous rounds]

--- FINAL SYNTHESIS ---
COLLECTIVE INTELLIGENCE OUTCOME
[Comprehensive insights from all perspectives]

KEY INSIGHTS
[Most valuable discoveries]

REMAINING UNCERTAINTIES
[What couldn't be resolved]

IMPLICATIONS
[Forward-looking insights for decision-making]
```

## Success Metrics
- Each round produces genuinely new insights
- Specialists maintain distinct valuable perspectives
- Web research continuously introduces fresh information
- Cross-pollination generates insights no single specialist would reach
- Different error types caught by different approaches
