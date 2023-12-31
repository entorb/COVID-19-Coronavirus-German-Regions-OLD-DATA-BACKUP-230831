#!/usr/bin/env python3.10
# by Dr. Torben Menke https://entorb.net
# https://github.com/entorb/COVID-19-Coronavirus-German-Regions
"""
plot a bar chart of various data
"""
import datetime as dt
import locale
import re

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

import helper

# Set German date format for plots: Okt instead of Oct

locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")


def read_alterstrukur() -> pd.DataFrame:
    """
    read Alterstruktur for DE
    """
    file = "data/DE_Bevoelkerung_nach_Altersgruppen-ges.tsv"

    df = pd.read_csv(file, sep="\t", index_col="Altersgruppe")

    df = df.rename(
        columns={"Personen": "Bevölkerung"},
        errors="raise",
    )
    de_sum = df["Bevölkerung"].loc["Summe"]
    df.drop("Summe", inplace=True)
    df.loc["20-"] = df.loc["0-9"] + df.loc["10-19"]
    df.loc["30-"] = df.loc["0-9"] + df.loc["10-19"] + df.loc["20-29"]
    df.loc["40-"] = df.loc["0-9"] + df.loc["10-19"] + df.loc["20-29"] + df.loc["30-39"]
    df.loc["20-40"] = df.loc["20-29"] + df.loc["30-39"]

    df["Bev_Proz"] = (df["Bevölkerung"] / de_sum * 100).round(1)

    return df


def read_rki_cases() -> pd.DataFrame:
    """
    read Excel file and perform some transformations
    here the date is in columns and the age group is in rows
    -> transpose to
    date as rows and age group as columns
    index: yearweek: 202014 für 2020 cw14
    """
    excelFile = "cache/de-rki-Altersverteilung.xlsx"
    df = pd.read_excel(
        open(excelFile, "rb"),  # noqa: SIM115
        sheet_name="Fallzahlen",
        engine="openpyxl",
    )
    assert df.columns[0] == "Altersgruppe", print(df.columns[0])
    assert df.columns[1] == "2020_10", print(df.columns[1])
    df.set_index("Altersgruppe", inplace=True)

    # # time-series of 7-Tage-Inzidenz might be intersting as well...
    # excelFile = "cache/de-rki-Altersverteilung.xlsx"
    # df_rki_inzidenz = pd.read_excel(
    #     open(excelFile, "rb"), sheet_name="7-Tage-Inzidenz", engine="openpyxl"
    # )
    # df_rki_inzidenz.set_index("Altersgruppe", inplace=True)
    # print(df_rki_inzidenz.head())

    # rename column header from 2020_14 to YearWeek : 202014 (int) etc.
    l2 = []
    cols_to_drop = []
    for c in df.columns:
        if re.match(r"^\d{4}_\d{1,2}$", c) is not None:
            year = int(c[0:4])
            week = int(c[5:7])
            l2.append(year * 100 + week)
        else:
            cols_to_drop.append(c)
    if cols_to_drop:
        print("dropping these columns:")
        print(df[cols_to_drop])
        df.drop(columns=cols_to_drop, inplace=True)
    # renaming the remaining columns to yearweek (int)
    df.columns = l2

    # transpose to have yearweek as index
    # print(df.head())
    df = df.transpose()
    df.index.name = "YearWeek"
    # print(df.head())

    # rename column headers
    l2 = []
    for c in df.columns:
        c = c.replace(" - ", "-")
        c = c.strip()  # remove tailing spaces
        l2.append(c)
    df.columns = l2

    # print(df.head())
    # exit()
    return df


def read_rki_deaths() -> pd.DataFrame:
    """
    read Excel file and perform some transformations
    here the date is in rows and the age group is in columns
    index: yearweek: 202014 für 2020 cw14
    """
    excelFile = "cache/de-rki-COVID-19_Todesfaelle.xlsx"

    df = pd.read_excel(
        open(excelFile, "rb"),  # noqa: SIM115
        sheet_name="COVID_Todesfälle_KW_AG10",
        engine="openpyxl",
    )

    # RKI uses "<4" for values 1,2,3, fixing this via assuming 1
    # TODO: calc replacement based on sum over all ages (Sheet: COVID_Todesfälle)
    df.replace(
        to_replace="<4",
        value=1,
        inplace=True,
        regex=False,
        # , limit=None, method="pad"
    )

    # convert str to int for all data columns
    for col in df.columns:
        df[col] = df[col].astype(int)

    # add YearWeek as index
    df["YearWeek"] = df["Sterbejahr"] * 100 + df["Sterbewoche"]

    df.set_index("YearWeek", inplace=True)
    df.drop(columns=["Sterbejahr", "Sterbewoche"], inplace=True)
    return df


def read_divi() -> pd.DataFrame:
    """
    read CSV file and perform some transformations
    here the date is in rows and the age group is in columns
    index: yearweek: 202014 für 2020 cw14
    """
    file_local = "cache/de-divi/bund-covid-altersstruktur-zeitreihe_ab-2021-04-29.csv"

    # read only first 10 chars from 2021-04-29T12:15:00+02:00
    pd_date_converter = lambda x: (x[0:10])  # noqa: E731
    df = pd.read_csv(
        file_local,
        sep=",",
        converters={"Datum": pd_date_converter},
        parse_dates=[
            "Datum",
        ],
    )
    df = df.rename(columns={"Datum": "Date"}, errors="raise")
    # df["Date"] = df["Datum"].str[0:10]
    # df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d")
    df["Year"] = pd.DatetimeIndex(df["Date"]).year
    df["Week"] = df["Date"].map(lambda v: pd.to_datetime(v).isocalendar()[1])
    df["YearWeek"] = df["Year"] * 100 + df["Week"]
    df.drop(columns=["Bundesland", "Date", "Week", "Year"], inplace=True)

    # print(df)

    # rename column headers
    # rename column headers by extracting some int values from a string
    l2 = []
    for col in df.columns:
        col = (
            col.replace("Stratum_", "").replace("_Bis_", "-").replace("80_Plus", "80+")
        )
        l2.append(col)
    df.columns = l2

    # group by and mean / average
    df = df.groupby(["YearWeek"]).mean()
    # .round(1)
    # df["sum"] = df.sum(axis=1)
    # .round(1)
    # print(df)

    return df


def filter_rki_cases(df_rki, start_yearweek: int = 202001, end_yearweek: int = 203053):
    """
    filters on yearweek
    returns DF, sum_cases
    """
    # optionally: filter on date range
    df_rki = df_rki[df_rki.index >= start_yearweek]
    df_rki = df_rki[df_rki.index <= end_yearweek]

    # calc sum and drop column
    sum_cases = df_rki["Gesamt"].sum()
    df_rki = df_rki.drop(
        "Gesamt",
        axis="columns",
    )
    print(f"{sum_cases} Fälle")

    d = {}
    for col in df_rki.columns:
        d[col] = df_rki[col].sum()

    # print(df_rki.head())
    # print(df_rki.columns)
    # print(df_rki["0-4"].head())
    # print(df_rki["5-9"].head())

    d2 = {
        "0-9": df_rki["0-4"].sum() + df_rki["5-9"].sum(),
        "10-19": df_rki["10-14"].sum() + df_rki["15-19"].sum(),
        "20-29": df_rki["20-24"].sum() + df_rki["25-29"].sum(),
        "30-39": df_rki["30-34"].sum() + df_rki["35-39"].sum(),
        "40-49": df_rki["40-44"].sum() + df_rki["45-49"].sum(),
        "50-59": df_rki["50-54"].sum() + df_rki["55-59"].sum(),
        "60-69": df_rki["60-64"].sum() + df_rki["65-69"].sum(),
        "70-79": df_rki["70-74"].sum() + df_rki["75-79"].sum(),
        "80-89": df_rki["80-84"].sum() + df_rki["85-89"].sum(),
        "80+": df_rki["80-84"].sum() + df_rki["85-89"].sum() + df_rki["90+"].sum(),
        "20-": df_rki["0-4"].sum()
        + df_rki["5-9"].sum()
        + df_rki["10-14"].sum()
        + df_rki["15-19"].sum(),
        "30-": df_rki["0-4"].sum()
        + df_rki["5-9"].sum()
        + df_rki["10-14"].sum()
        + df_rki["15-19"].sum()
        + df_rki["20-24"].sum()
        + df_rki["25-29"].sum(),
        "40-": df_rki["0-4"].sum()
        + df_rki["5-9"].sum()
        + df_rki["10-14"].sum()
        + df_rki["15-19"].sum()
        + df_rki["20-24"].sum()
        + df_rki["25-29"].sum()
        + df_rki["30-34"].sum()
        + df_rki["35-39"].sum(),
        "20-40": df_rki["20-24"].sum()
        + df_rki["25-29"].sum()
        + df_rki["30-34"].sum()
        + df_rki["35-39"].sum(),
    }
    # merge dicts
    d.update(d2)
    df = pd.DataFrame.from_dict(d, orient="index", columns=["Covid_Fälle"])
    df["Covid_Fälle_Proz"] = (df["Covid_Fälle"] / sum_cases * 100).round(1)

    # print(df)
    return (df, sum_cases)


def filter_rki_deaths(df_rki, start_yearweek: int = 202001, end_yearweek: int = 203053):
    """
    returns df, sum
    """
    # optionally: filter on date range
    df_rki = df_rki[df_rki.index >= start_yearweek]
    df_rki = df_rki[df_rki.index <= end_yearweek]

    # calc sum
    sum_death = 0
    for col in df_rki.columns:
        sum_death += df_rki[col].sum()
    print(f"{sum_death} Deaths")

    d = {
        "0-9": df_rki["AG 0-9 Jahre"].sum(),
        "10-19": df_rki["AG 10-19 Jahre"].sum(),
        "20-29": df_rki["AG 20-29 Jahre"].sum(),
        "30-39": df_rki["AG 30-39 Jahre"].sum(),
        "40-49": df_rki["AG 40-49 Jahre"].sum(),
        "50-59": df_rki["AG 50-59 Jahre"].sum(),
        "60-69": df_rki["AG 60-69 Jahre"].sum(),
        "70-79": df_rki["AG 70-79 Jahre"].sum(),
        "80+": df_rki["AG 80-89 Jahre"].sum() + df_rki["AG 90+ Jahre"].sum(),
        "80-89": df_rki["AG 80-89 Jahre"].sum(),
        "90+": df_rki["AG 90+ Jahre"].sum(),
        "20-": df_rki["AG 0-9 Jahre"].sum() + df_rki["AG 10-19 Jahre"].sum(),
        "30-": df_rki["AG 0-9 Jahre"].sum()
        + df_rki["AG 10-19 Jahre"].sum()
        + df_rki["AG 20-29 Jahre"].sum(),
        "40-": df_rki["AG 0-9 Jahre"].sum()
        + df_rki["AG 10-19 Jahre"].sum()
        + df_rki["AG 20-29 Jahre"].sum()
        + df_rki["AG 30-39 Jahre"].sum(),
        "20-40": df_rki["AG 20-29 Jahre"].sum() + df_rki["AG 30-39 Jahre"].sum(),
    }
    df = pd.DataFrame.from_dict(d, orient="index", columns=["Covid_Tote"])
    df["Covid_Tote_Proz"] = (df["Covid_Tote"] / sum_death * 100).round(3)
    # print(df)

    return (df, sum_death)


def filter_divi(df_divi, start_yearweek: int = 202001, end_yearweek: int = 203053):
    # print(df_divi)
    # optionally: filter on date range
    df_divi = df_divi[df_divi.index >= start_yearweek]
    df_divi = df_divi[df_divi.index <= end_yearweek]

    # sum_icu = 0
    # for col in df_divi.columns:
    #     sum_icu += df_divi[col].sum()
    # print(f"{sum_icu} ICU")

    # print(df_divi)
    # df = df_divi["sum"].mean()
    # df[]
    # print(df_divi)
    # exit()

    d = {}
    for col in df_divi.columns:
        d[col] = df_divi[col].mean()

    df = pd.DataFrame.from_dict(d, orient="index", columns=["ICU"])
    # print(df)
    # sum_icu includes the unknown age fraction
    sum_icu = int(df["ICU"].sum())
    df.drop("Unbekannt", inplace=True)
    # sum_icu does not include the unknown age fraction
    sum_icu2 = int(df["ICU"].sum())
    df["ICU"] = df["ICU"].round(0).astype(int)
    df.loc["0-9"] = df.loc["17_Minus"] / 2  # This is an estimation
    df.loc["10-19"] = df.loc["17_Minus"] / 2  # This is an estimation
    df.loc["20-29"] = df.loc["18-29"]  # This is an estimation
    df.loc["20-"] = df.loc["17_Minus"]  # This is an estimation
    df.loc["30-"] = df.loc["17_Minus"] + df.loc["18-29"]
    df.loc["40-"] = df.loc["17_Minus"] + df.loc["18-29"] + df.loc["30-39"]
    df.loc["20-40"] = df.loc["18-29"] + df.loc["30-39"]  # This is an estimation

    df["ICU_Proz"] = (df["ICU"] / sum_icu2 * 100).round(1)

    # print(df)

    # exit()

    return df, sum_icu


def plotit(df, outfile, title_time, sum_cases: int, sum_deaths: int, sum_icu: int):
    # initialize plot
    axes = [None]
    fig, axes[0] = plt.subplots(nrows=1, ncols=1, sharex=True, dpi=100, figsize=(8, 6))

    # select subset of columns
    df = df[["Bev_Proz", "Covid_Fälle_Proz", "ICU_Proz", "Covid_Tote_Proz"]]
    # drop null value rows
    df = df.dropna()
    # print(df)
    # manually drop some rows
    # df = df.drop("80-89").drop("90+")

    myPlot = df.plot.barh(
        legend=True,
        use_index=True,
        linewidth=2.0,
        zorder=1,
        width=0.8,
        color=["green", "blue", "red", "black"],
        figsize=(8, 8),
    )
    plt.legend(
        [
            "Anteil ges. Bevölkerung",
            "Anteil ges. Covid Fälle",
            "Anteil Intensivbetten (gemittelt)",
            "Anteil ges. Covid Tote",
        ],
    )

    plt.gca().invert_yaxis()
    # myPlot.set_xlim(0.1, 100)
    # plt.gca().set_xscale("log")
    myPlot.set_xlim(0, 68)
    plt.gca().xaxis.set_major_formatter(mtick.PercentFormatter())
    plt.gca().xaxis.set_major_locator(mtick.MultipleLocator(5))

    plt.title(
        f"Covid pro Altersgruppe in DE {title_time}\n{sum_cases} Fälle, {sum_deaths} Tote, {sum_icu} ICU Betten (gemittelt)",
    )

    # plt.xlabel("Prozent")
    plt.grid(axis="x")
    plt.ylabel("Altersgruppe (Jahre)")
    fig.set_tight_layout(True)
    helper.mpl_add_text_source(
        source="RKI and DIVI",
        date=(dt.date.today() - dt.timedelta(days=1)),
    )

    plt.savefig(fname=f"plots-python/{outfile}.png", format="png")


def main():
    # fetch_rki_cases()
    file_local = "cache/de-rki-Altersverteilung.xlsx"
    url = "https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Daten/Altersverteilung.xlsx?__blob=publicationFile"
    helper.download_from_url_if_old(url=url, file_local=file_local)

    # fetch_rki_deaths()
    file_local = "cache/de-rki-COVID-19_Todesfaelle.xlsx"
    url = "https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Projekte_RKI/COVID-19_Todesfaelle.xlsx?__blob=publicationFile"
    helper.download_from_url_if_old(url=url, file_local=file_local)

    # fetch_divi()
    file_local = "cache/de-divi/bund-covid-altersstruktur-zeitreihe_ab-2021-04-29.csv"
    url = "https://diviexchange.blob.core.windows.net/%24web/bund-covid-altersstruktur-zeitreihe_ab-2021-04-29.csv"
    helper.download_from_url_if_old(url=url, file_local=file_local)

    df_rki_deaths = read_divi()

    df_alterstrukur = read_alterstrukur()
    df_rki_cases = read_rki_cases()
    df_rki_deaths = read_rki_deaths()
    df_divi_icu = read_divi()

    start_year = 2020
    start_week = 1
    end_year = 2021
    end_week = 25

    df_cases, sum_cases = filter_rki_cases(
        df_rki=df_rki_cases,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )
    df_deaths, sum_deaths = filter_rki_deaths(
        df_rki=df_rki_deaths,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )
    df_icu, sum_icu = filter_divi(
        df_divi=df_divi_icu,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )

    df = df_cases.join([df_deaths, df_alterstrukur, df_icu])
    # print(df)
    plotit(
        df=df,
        outfile="de_age_percent_1_pre_2021_summer",
        title_time="bis Sommer 2021",
        sum_cases=sum_cases,
        sum_deaths=sum_deaths,
        sum_icu=sum_icu,
    )
    df.sort_index(inplace=True)
    df.to_csv(
        "data/de_age_percent_1_pre_2021_summer.tsv",
        sep="\t",
        index=True,
        lineterminator="\n",
    )

    start_year = 2021
    start_week = 26
    end_year = 2030
    end_week = 1

    df_cases, sum_cases = filter_rki_cases(
        df_rki=df_rki_cases,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )
    df_deaths, sum_deaths = filter_rki_deaths(
        df_rki=df_rki_deaths,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )
    df_icu, sum_icu = filter_divi(
        df_divi=df_divi_icu,
        start_yearweek=start_year * 100 + start_week,
        end_yearweek=end_year * 100 + end_week,
    )

    df = df_cases.join([df_deaths, df_alterstrukur, df_icu])
    # print(df)
    plotit(
        df=df,
        outfile="de_age_percent_2_post_2021_summer",
        title_time="seit Sommer 2021",
        sum_cases=sum_cases,
        sum_deaths=sum_deaths,
        sum_icu=sum_icu,
    )
    df.sort_index(inplace=True)
    df.to_csv(
        "data/de_age_percent_2_post_2021_summer.tsv",
        sep="\t",
        index=True,
        lineterminator="\n",
    )


if __name__ == "__main__":
    main()
