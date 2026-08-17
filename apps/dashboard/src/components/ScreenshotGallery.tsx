import type { Step } from "../api/client";

export default function ScreenshotGallery({ steps }: { steps: Step[] }) {
  const withScreenshots = steps.filter((s) => s.screenshot_path);

  if (withScreenshots.length === 0) {
    return <p>No screenshots captured for this run.</p>;
  }

  return (
    <div className="gallery">
      {withScreenshots.map((step) => (
        <figure key={step.id}>
          <img src={step.screenshot_path ?? ""} alt={`Step ${step.index} screenshot`} />
          <figcaption>Step {step.index}</figcaption>
        </figure>
      ))}
    </div>
  );
}
