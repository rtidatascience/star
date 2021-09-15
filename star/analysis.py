# This script accepts a dataframe and returns information about analysis

import numpy as np
import pandas as pd
import statsmodels
import statsmodels.api as sm
from scipy import stats
from scipy.special import expit


class Analysis:
    def __init__(self):
        pass

    def analyze(self, df, analysis_type="regression", subset="single"):

        if subset == "single":

            if analysis_type == "simple":
                return self.simple(df)

            elif analysis_type == "fisher":
                return self.fisher_exact(df)

            elif analysis_type == "regression":
                return self.regression(df)

        elif subset == "inspect":
            return self.inspect(df)

    # Very simple analysis, simply looks at the difference in variable
    # between night and day
    def simple(self, df):
        crosstab = pd.crosstab(df["target"], df["light"])

        target_day_proportion = crosstab[1][1] / (crosstab[1][1] + crosstab[1][0])
        target_night_proportion = crosstab[0][1] / (crosstab[0][1] + crosstab[0][0])

        # Percentage increase in day stops for the target vs. night stops,
        # within the intertwilight period
        return np.round(
            (target_day_proportion - target_night_proportion)
            / target_day_proportion
            * 100,
            decimals=2,
        )

    # Gives p-value for our simple comparison using Fisher's Exact Test
    def fisher_exact(self, df):

        crosstab = pd.crosstab(df["target"], df["light"])

        # Odds ratio and p-value of the two-sided Fisher's Exact Test
        # Maybe we need to correct this p-value based on sample size --
        # leaving uncorrected for now

        return stats.fisher_exact(crosstab)

    # Perform Taniguichi Regression
    def regression(self, df):

        # Add intercept

        df["intercept"] = 1

        # If officer_id is provided, we perform the GEE regression otherwise,
        #  we do a normal logit
        # Per Gayle Bieler we are using an Exchangable covariance structure.
        #  Perhaps a naive, rather than robust,
        # covariance type is justified, but we would need some sort of test
        # to determine that

        if "officerid" in df.columns:
            officer_formula = (
                "target ~ C(light) + bs(time_in_seconds, 6) + C(year) + C(day_of_week)"
            )
            logit = sm.GEE.from_formula(
                officer_formula,
                "officerid",
                df,
                family=sm.families.Binomial(sm.families.links.logit),
                cov_struct=sm.cov_struct.Exchangeable(),
            )

            fitted = logit.fit()

            marginal_effect_day = (
                statsmodels.genmod.generalized_estimating_equations.GEEMargins(
                    results=fitted, args=("overall", "dydx", None, False, False)
                ).margeff[0]
            )

            # Finding median predicited probabilities at each level of light
            df["fitted_values"] = fitted.fittedvalues
            dark_prob = df[df["light"] == 0].fitted_values.median() * 100
            light_prob = df[df["light"] == 1].fitted_values.median() * 100

        else:
            logit_formula = (
                "target ~ C(light) + bs(time_in_seconds, 6) + C(year) + C(day_of_week)"
            )
            logit = sm.Logit.from_formula(
                logit_formula,
                df,
            )
            fitted = logit.fit()

            marginal_effect_day = fitted.get_margeff(at="overall").margeff[0]

            # Finding median predicited probabilities at each level of light
            # For some mysterious reason, the sm.Logit returns non-transformed
            # fitted values, so we apply the logit transform
            df["fitted_values"] = expit(fitted.fittedvalues)
            dark_prob = df[df["light"] == 0].fitted_values.median() * 100
            light_prob = df[df["light"] == 1].fitted_values.median() * 100

        summary = fitted.summary()
        odds_ratios = np.exp(fitted.params)
        p_values = fitted.pvalues
        odds_ratio_day = odds_ratios["C(light)[T.1]"]
        p_value_day = p_values["C(light)[T.1]"]
        risk_ratio_day = 0.5
        print(summary.as_text())
        model_summary_html = summary.as_html()
        return {
            "model_summary_html": model_summary_html,
            "odds_ratio_day": odds_ratio_day,
            "p_value_day": p_value_day,
            "risk_ratio_day": risk_ratio_day,
            "marginal_effect_day": marginal_effect_day,
            "light_prob": light_prob,
            "dark_prob": dark_prob,
        }
