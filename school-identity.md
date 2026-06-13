# School identity ledger — control, switches, mergers & closures

_Seeded 2026-06-13 from the ABA master `Basics.SchoolType` (198/210 schools)
with the 13 closed/merged schools filled from institutional history. The
per-school **control** value is now tracked in `data/exhibit-data.js`
(`control`: `Public` | `Private`), with `control_switch_year` + `control_note`
on schools that changed control._

## Current control (most recent cycle)
- **Public:** 87
- **Private:** 123
- **Total:** 210

## Control changes — private ↔ public
| School | Change | Year | Note |
|---|---|---|---|
| UIC — University of Illinois Chicago | Private → **Public** | 2019 | Was the private *John Marshall Law School (Chicago)*; acquired by the University of Illinois and converted to public. (Distinct from *Atlanta's* John Marshall, still private.) |
| Texas A&M University | Private → **Public** | 2013 | Acquired the private *Texas Wesleyan School of Law* and converted it to a public school. |
| Penn State Dickinson Law | Private → **Public** | ~1997–2015 | Historic private Dickinson School of Law integrated into Penn State (public); predates the 2011–2025 data window. Listed for completeness. |

> Tracked in data as `control_switch_year` + `control_note` (UIC 2019, Texas A&M 2013).
> If you know of others inside 2011–2025, add them here and to the data.

## Mergers, splits & renames
| School / event | Type | Year | Note |
|---|---|---|---|
| Mitchell Hamline School of Law | Merger | 2015 | *William Mitchell College of Law* + *Hamline University School of Law* combined. Both pre-merger entities end 2015 in the data; Mitchell Hamline begins 2016. (Private.) |
| Widener (Delaware) + Widener (Commonwealth/PA) | Split | ~2015 | Widener University School of Law split into two separately-reporting schools. (Both Private.) |
| Rutgers Law School | Merger | 2015 | *Rutgers–Camden* + *Rutgers–Newark* unified into one school. (Public.) |
| UC Law San Francisco | Rename | 2023 | Formerly *UC Hastings College of the Law*; renamed (dropped "Hastings"). No control change (Public). |


## Closures & accreditation losses
| School | Event | Year | Note |
|---|---|---|---|
| Charlotte School of Law | Closed | 2017 | Private; lost federal aid eligibility, closed. |
| Indiana Tech Law School | Closed | 2017 | Private; closed after ~4 years. |
| Arizona Summit Law School | Closed | 2018 | Private (InfiLaw); lost ABA accreditation, closed. |
| Whittier Law School | Closed | 2017–2020 | Private; stopped enrolling 2017, teach-out through 2020. |
| Valparaiso University Law | Closed | 2020 | Private; teach-out. |
| Concordia University School of Law | Closed | ~2020 | Private (Idaho). |
| Florida Coastal School of Law | Closed | 2021 | Private (InfiLaw); closed. |
| Thomas Jefferson School of Law | Lost ABA accreditation | 2019 | Private; continued under California (state) accreditation. |
| Hamline University School of Law | Merged | 2015 | → Mitchell Hamline (see mergers). |
| William Mitchell College of Law | Merged | 2015 | → Mitchell Hamline (see mergers). |


## Full control list (210 schools)
| School | Control |
|---|---|
| Albany Law School | Private |
| American University | Private |
| Appalachian | Private |
| Arizona State University | Public |
| Arizona Summit Law School | Private |
| Arkansas | Public |
| Arkansas at Little Rock | Public |
| Atlanta's John Marshall Law School | Private |
| Ave Maria | Private |
| Baltimore | Public |
| Barry University | Private |
| Baylor University | Private |
| Belmont University | Private |
| Boston College | Private |
| Boston University | Private |
| Brigham Young University | Private |
| Brooklyn Law School | Private |
| Buffalo, University at | Public |
| California Western | Private |
| California-Berkeley | Public |
| California-Davis | Public |
| California-Irvine | Public |
| California-Los Angeles | Public |
| California-San Francisco | Public |
| Campbell University | Private |
| Capital University Law School | Private |
| Cardozo, Yeshiva University | Private |
| Case Western Reserve University | Private |
| Catholic University of America | Private |
| Chapman University | Private |
| Charleston | Private |
| Charlotte School of Law | Private |
| Chicago-Kent, Illinois Institute of Technology | Private |
| Cincinnati | Public |
| City University of New York | Public |
| Cleveland State University | Public |
| Colorado | Public |
| Columbia University | Private |
| Concordia Law School | Private |
| Connecticut | Public |
| Cooley Law School | Private |
| Cornell University | Private |
| Creighton University | Private |
| Dayton | Private |
| Denver | Private |
| DePaul University | Private |
| Detroit Mercy | Private |
| District of Columbia | Public |
| Drake University | Private |
| Drexel University | Private |
| Duke University | Private |
| Duquesne University | Private |
| Elon University | Private |
| Emory University | Private |
| Faulkner University | Private |
| Florida | Public |
| Florida A&M University | Public |
| Florida Coastal School of Law | Private |
| Florida International University | Public |
| Florida State University | Public |
| Fordham University | Private |
| George Mason University | Public |
| George Washington University | Private |
| Georgetown University | Private |
| Georgia | Public |
| Georgia State University | Public |
| Golden Gate University | Private |
| Gonzaga University | Private |
| Hamline University | Private |
| Harvard University | Private |
| Hawaii | Public |
| High Point University | Private |
| Hofstra University | Private |
| Houston | Public |
| Howard University | Private |
| Idaho | Public |
| Illinois | Public |
| Illinois-Chicago | Public |
| Indiana Tech | Private |
| Indiana University-Bloomington | Public |
| Indiana University-Indianapolis | Public |
| Inter American University of Puerto Rico | Private |
| Iowa | Public |
| Jacksonville University | Private |
| Kentucky | Public |
| La Verne University Of | Private |
| Lewis & Clark Law School | Private |
| Liberty University | Private |
| Lincoln Memorial University | Private |
| Louisiana State University | Public |
| Louisville | Public |
| Loyola Marymount University-Los Angeles | Private |
| Loyola University-Chicago | Private |
| Loyola University-New Orleans | Private |
| Maine | Public |
| Marquette University | Private |
| Maryland | Public |
| Massachusetts/Dartmouth | Public |
| Mercer University | Private |
| Miami | Private |
| Michigan | Public |
| Michigan State University | Public |
| Minnesota | Public |
| Mississippi College | Private |
| Missouri | Public |
| Missouri-Kansas City | Public |
| Mitchell/Hamline | Private |
| Montana | Public |
| Nebraska | Public |
| Nevada-Las Vegas | Public |
| New England Law/Boston | Private |
| New Hampshire | Public |
| New York Law School | Private |
| New York University | Private |
| North Carolina | Public |
| North Carolina Central University | Public |
| North Dakota | Public |
| North Texas at Dallas | Public |
| Northeastern University | Private |
| Northern Illinois University | Public |
| Northern Kentucky University | Public |
| Northwestern University | Private |
| Notre Dame | Private |
| Nova Southeastern University | Private |
| Ohio Northern University | Private |
| Oklahoma | Public |
| Oklahoma City University | Private |
| Oregon | Public |
| Pace University | Private |
| Penn State Dickinson Law | Public |
| Penn State Law (University Park) | Public |
| Pennsylvania | Private |
| Pepperdine University | Private |
| Pittsburgh | Public |
| Pontifical Catholic University of Puerto Rico | Private |
| Puerto Rico | Public |
| Quinnipiac University | Private |
| Regent University | Private |
| Richmond | Private |
| Roger Williams University | Private |
| Rutgers University | Public |
| Saint Louis University | Private |
| Samford University | Private |
| San Diego | Private |
| San Francisco | Private |
| Santa Clara University | Private |
| Seattle University | Private |
| Seton Hall University | Private |
| South Carolina | Public |
| South Dakota | Public |
| South Texas Houston | Private |
| Southern California | Private |
| Southern Illinois University | Public |
| Southern Methodist University | Private |
| Southern University | Public |
| Southwestern Law School | Private |
| St. John's University | Private |
| St. Mary's University | Private |
| St. Thomas University (Miami) | Private |
| Stanford University | Private |
| Stetson University | Private |
| Suffolk University | Private |
| Syracuse University | Private |
| Temple University | Public |
| Tennessee | Public |
| Texas | Public |
| Texas A&M University | Public |
| Texas Southern University | Public |
| Texas Tech University | Public |
| The Ohio State University | Public |
| Thomas Jefferson School of Law | Private |
| Touro University | Private |
| Tulane University | Private |
| University of Akron | Public |
| University of Alabama | Public |
| University of Arizona | Public |
| University of Chicago | Private |
| University of Kansas | Public |
| University of Memphis | Public |
| University of Mississippi | Public |
| University of New Mexico | Public |
| University of St. Thomas (Minnesota) | Private |
| University of the Pacific | Private |
| University of Toledo | Public |
| University of Tulsa | Private |
| University of Utah | Public |
| Valparaiso University | Private |
| Vanderbilt University | Private |
| Vermont Law School | Private |
| Villanova University | Private |
| Virginia | Public |
| Wake Forest University | Private |
| Washburn University | Public |
| Washington | Public |
| Washington and Lee University | Private |
| Washington University (St. Louis) | Private |
| Wayne State University | Public |
| West Virginia University | Public |
| Western New England University | Private |
| Western State, Westcliff University | Private |
| Whittier Law School | Private |
| Widener University Commonwealth Law School | Private |
| Widener University Delaware Law School | Private |
| Willamette University | Private |
| William & Mary | Public |
| William Mitchell College of Law | Private |
| Wilmington University | Private |
| Wisconsin | Public |
| Wyoming | Public |
| Yale University | Private |

