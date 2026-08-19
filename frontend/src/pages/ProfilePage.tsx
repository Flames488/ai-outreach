import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { ErrorState, LoadingState } from "../components/States";

function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function listToLines(value: unknown[] | null | undefined): string {
  if (!value) return "";
  return value.map((v) => (typeof v === "string" ? v : JSON.stringify(v))).join("\n");
}

export function ProfilePage() {
  const queryClient = useQueryClient();
  const meQuery = useQuery({ queryKey: ["me"], queryFn: api.me });

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [country, setCountry] = useState("");
  const [city, setCity] = useState("");
  const [currentPosition, setCurrentPosition] = useState("");
  const [yearsOfExperience, setYearsOfExperience] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [workAuthorization, setWorkAuthorization] = useState("");
  const [visaSponsorshipNeeded, setVisaSponsorshipNeeded] = useState(false);
  const [expectedSalary, setExpectedSalary] = useState("");
  const [noticePeriod, setNoticePeriod] = useState("");
  const [education, setEducation] = useState("");
  const [certifications, setCertifications] = useState("");
  const [languages, setLanguages] = useState("");
  const [professionalSummary, setProfessionalSummary] = useState("");
  const [skills, setSkills] = useState("");
  const [desiredTitles, setDesiredTitles] = useState("");
  const [notableProjects, setNotableProjects] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const profile = meQuery.data?.profile;
    if (!profile || hydrated) return;
    setFullName(profile.full_name ?? "");
    setPhone(profile.phone ?? "");
    setCountry(profile.country ?? "");
    setCity(profile.city ?? "");
    setCurrentPosition(profile.current_position ?? "");
    setYearsOfExperience(profile.years_of_experience?.toString() ?? "");
    setLinkedinUrl(profile.linkedin_url ?? "");
    setGithubUrl(profile.github_url ?? "");
    setPortfolioUrl(profile.portfolio_url ?? "");
    setWorkAuthorization(profile.work_authorization ?? "");
    setVisaSponsorshipNeeded(profile.visa_sponsorship_needed ?? false);
    setExpectedSalary(profile.expected_salary?.toString() ?? "");
    setNoticePeriod(profile.notice_period ?? "");
    setEducation(listToLines(profile.education));
    setCertifications(listToLines(profile.certifications));
    setLanguages(listToLines(profile.languages));
    setProfessionalSummary(profile.professional_summary ?? "");
    setSkills(listToLines(profile.skills));
    setDesiredTitles(listToLines(profile.desired_titles));
    setNotableProjects(listToLines(profile.notable_projects));
    setHydrated(true);
  }, [meQuery.data, hydrated]);

  const saveMutation = useMutation({
    mutationFn: api.updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  if (meQuery.isLoading) return <LoadingState />;
  if (meQuery.isError) return <ErrorState message="Could not load your profile." />;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    saveMutation.mutate({
      full_name: fullName || null,
      phone: phone || null,
      country: country || null,
      city: city || null,
      current_position: currentPosition || null,
      years_of_experience: yearsOfExperience ? Number(yearsOfExperience) : null,
      linkedin_url: linkedinUrl || null,
      github_url: githubUrl || null,
      portfolio_url: portfolioUrl || null,
      work_authorization: workAuthorization || null,
      visa_sponsorship_needed: visaSponsorshipNeeded,
      expected_salary: expectedSalary ? Number(expectedSalary) : null,
      notice_period: noticePeriod || null,
      education: linesToList(education),
      certifications: linesToList(certifications),
      languages: linesToList(languages),
      professional_summary: professionalSummary || null,
      skills: linesToList(skills),
      desired_titles: linesToList(desiredTitles),
      notable_projects: linesToList(notableProjects),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Profile</h1>
        <p className="mt-1 text-sm text-slate-500">
          This is what the AI compares against every job it finds — the more complete, the better
          the match scores and generated cover letters will be. There's no CV file to upload here;
          it's this structured profile the AI reads, not a parsed PDF.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card space-y-4 p-6">
          <h2 className="text-sm font-semibold text-slate-700">Basics</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Full name</label>
              <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div>
              <label className="label">Phone</label>
              <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <div>
              <label className="label">Country</label>
              <input className="input" value={country} onChange={(e) => setCountry(e.target.value)} />
            </div>
            <div>
              <label className="label">City</label>
              <input className="input" value={city} onChange={(e) => setCity(e.target.value)} />
            </div>
          </div>
        </section>

        <section className="card space-y-4 p-6">
          <h2 className="text-sm font-semibold text-slate-700">What you're looking for</h2>
          <p className="text-xs text-slate-400">
            This is the strongest signal the AI uses to score and rank jobs — the more specific,
            the better the matches.
          </p>
          <div>
            <label className="label">Professional summary</label>
            <textarea
              className="input min-h-24"
              placeholder="Results-driven Programmer, Web Developer, Web Designer and AI Automation Specialist with 5+ years experience building scalable digital solutions..."
              value={professionalSummary}
              onChange={(e) => setProfessionalSummary(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Desired job titles — one per line</label>
            <textarea
              className="input min-h-20"
              placeholder={"Web Developer\nAI Automation Specialist\nBackend Developer"}
              value={desiredTitles}
              onChange={(e) => setDesiredTitles(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Skills — one per line</label>
            <textarea
              className="input min-h-24"
              placeholder={"Web Development\nFrontend Development\nBackend Development\nAI Automation\nAPI Integration"}
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Notable projects — one per line</label>
            <textarea
              className="input min-h-20"
              placeholder={"Vitar – www.livevault.cloud\nCodebrix Web – www.codebrixweb.com"}
              value={notableProjects}
              onChange={(e) => setNotableProjects(e.target.value)}
            />
          </div>
        </section>

        <section className="card space-y-4 p-6">
          <h2 className="text-sm font-semibold text-slate-700">Experience</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Current position</label>
              <input
                className="input"
                placeholder="e.g. Senior Backend Engineer"
                value={currentPosition}
                onChange={(e) => setCurrentPosition(e.target.value)}
              />
            </div>
            <div>
              <label className="label">Years of experience</label>
              <input
                className="input"
                type="number"
                min="0"
                value={yearsOfExperience}
                onChange={(e) => setYearsOfExperience(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="label">Education — one entry per line</label>
            <textarea
              className="input min-h-20"
              placeholder="B.Sc. Computer Science, University of Lagos, 2022"
              value={education}
              onChange={(e) => setEducation(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Certifications — one per line</label>
            <textarea
              className="input min-h-16"
              value={certifications}
              onChange={(e) => setCertifications(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Languages — one per line</label>
            <textarea
              className="input min-h-16"
              placeholder="English (fluent)"
              value={languages}
              onChange={(e) => setLanguages(e.target.value)}
            />
          </div>
        </section>

        <section className="card space-y-4 p-6">
          <h2 className="text-sm font-semibold text-slate-700">Links</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="label">LinkedIn</label>
              <input className="input" value={linkedinUrl} onChange={(e) => setLinkedinUrl(e.target.value)} />
            </div>
            <div>
              <label className="label">GitHub</label>
              <input className="input" value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} />
            </div>
            <div>
              <label className="label">Portfolio</label>
              <input className="input" value={portfolioUrl} onChange={(e) => setPortfolioUrl(e.target.value)} />
            </div>
          </div>
        </section>

        <section className="card space-y-4 p-6">
          <h2 className="text-sm font-semibold text-slate-700">Logistics</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Work authorization</label>
              <input
                className="input"
                placeholder="e.g. Nigerian citizen, requires sponsorship"
                value={workAuthorization}
                onChange={(e) => setWorkAuthorization(e.target.value)}
              />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={visaSponsorshipNeeded}
                  onChange={(e) => setVisaSponsorshipNeeded(e.target.checked)}
                />
                Needs visa sponsorship
              </label>
            </div>
            <div>
              <label className="label">Expected salary (annual, USD)</label>
              <input
                className="input"
                type="number"
                min="0"
                value={expectedSalary}
                onChange={(e) => setExpectedSalary(e.target.value)}
              />
            </div>
            <div>
              <label className="label">Notice period</label>
              <input
                className="input"
                placeholder="e.g. Immediately available"
                value={noticePeriod}
                onChange={(e) => setNoticePeriod(e.target.value)}
              />
            </div>
          </div>
        </section>

        {saveMutation.isError && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {saveMutation.error instanceof ApiError
              ? saveMutation.error.message
              : "Could not save your profile."}
          </p>
        )}

        <button type="submit" className="btn-primary" disabled={saveMutation.isPending}>
          {saveMutation.isSuccess && !saveMutation.isPending ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : null}
          {saveMutation.isPending ? "Saving…" : saveMutation.isSuccess ? "Saved" : "Save profile"}
        </button>
      </form>
    </div>
  );
}
