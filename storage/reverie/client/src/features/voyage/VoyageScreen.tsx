import { useEffect, useState } from 'react'
import { api } from '@/shared/lib/api'
import BottomNav from '@/shared/ui/BottomNav'

interface Port { name: string; date: string; type: string; subtitle?: string; notes: string }
interface Itinerary {
  voyage_name: string; ship: string; cabin: string; route: string
  booking_ref?: string
  embark_date: string; disembark_date: string
  full_journey_days: number; full_journey_start: string; ports: Port[]
}
interface Booking { type: string; description: string; confirmation: string; status: string; amount_usd: number }
interface BookingsResp { bookings: Booking[] }
interface WeatherForecast {
  port: string; date: string; type: string
  forecast: { temp_high_f: number; temp_low_f: number; wind_max_mph: number; condition: string } | null
}
interface WeatherResp { forecasts: WeatherForecast[] }
interface DayDetail {
  excursion?: { title: string; time?: string; duration?: string; conf?: string; operator?: string; cost?: number }
  dining?: { restaurant: string; time: string; cost?: number; status?: string }
}

type Tab = 'itinerary' | 'bookings'

const TYPE_STYLES: Record<string, { badge: string; border: string }> = {
  'pre-cruise':  { badge: 'bg-ether/20 text-ether', border: 'border-ether/30' },
  'post-cruise': { badge: 'bg-ether/20 text-ether', border: 'border-ether/30' },
  embark:        { badge: 'bg-gold/20 text-gold', border: 'border-gold/50' },
  disembark:     { badge: 'bg-gold/20 text-gold', border: 'border-gold/50' },
  port:          { badge: 'bg-witness/20 text-witness', border: 'border-witness/30' },
  sea:           { badge: 'bg-between text-dusk', border: 'border-between' },
  excursion:     { badge: 'bg-gold/20 text-gold', border: 'border-gold/30' },
}
const BOOKING_COLORS: Record<string, string> = {
  flight: 'text-ether', hotel: 'text-witness', cruise: 'text-gold',
  excursion: 'text-gold', transfer: 'text-dusk',
}

// Pexels CDN helper
const px = (id: number | string, ext = 'jpeg') =>
  `https://images.pexels.com/photos/${id}/pexels-photo-${id}.${ext}?auto=compress&cs=tinysrgb&dpr=2&h=800&w=1200`

// Per-date hero images — one unique photo per day, no repeated lookups
// McLeod/McGlasson Silver Muse Mediterranean 2026
const DATE_IMAGES: Record<string, string> = {
  '2026-06-18': px(6700045),    // Overnight departure — airport terminal
  '2026-06-19': px(2225442),    // Rome arrival — Via Veneto golden hour
  '2026-06-20': px(2422497),    // Rome — Colosseum Arena Floor & Forum
  '2026-06-21': px(1797158),    // Florence day trip — Duomo cathedral
  '2026-06-22': px(2253884),    // Rome — Vatican & St. Peter's Basilica
  '2026-06-23': px(5200278),    // Civitavecchia embarkation — Silver Muse
  '2026-06-24': px(4371473),    // Naples — Bay of Naples & Herculaneum
  '2026-06-25': px(3576559),    // Giardini Naxos — Taormina clifftop theater
  '2026-06-26': px(13181958),   // Siracusa — Baroque Noto piazza
  '2026-06-27': px(1440476),    // Valletta — Malta limestone harbor
  '2026-06-28': px(2070485),    // Sea day — Adriatic seascape
  '2026-06-29': px(1658967),    // Kotor — Bay of Montenegro fjord
  '2026-06-30': px(1680247),    // Dubrovnik — Adriatic walled city
  '2026-07-01': px(4534200),    // Split — Diocletian's Palace promenade
  '2026-07-02': px(2680493),    // Zadar — Dalmatian coast
  '2026-07-03': px(1796678),    // Venice arrival — Grand Canal water taxi
  '2026-07-04': px(3629536),    // Venice — canals & bridges from above
  '2026-07-05': px(2058404),    // Venice final evening — gondola at dusk
}

function getImage(port: Port): string {
  return DATE_IMAGES[port.date] ?? px(2070485)
}

// Structured day details — McLeod/McGlasson Silver Muse Mediterranean (SM260623010)
// Source: dossier + booking 298475-25 + GetYourGuide orders — Jun 12 2026
const DAY_DETAILS: Record<string, DayDetail> = {
  // Pre-cruise excursions (GetYourGuide)
  '2026-06-20': { excursion: { title: 'Colosseum with Arena Floor, Roman Forum & Palatine Hill', time: '10:00', duration: '3 hrs', operator: 'GetYourGuide', cost: 301.86 } },
  '2026-06-21': { excursion: { title: 'Uffizi Gallery + Michelangelo\'s David + Gelato Walk', time: '09:30', duration: '3 hrs', operator: 'GetYourGuide · Train ref JJQ6Z5', cost: 257.96 } },
  '2026-06-22': { excursion: { title: 'Vatican Museums, Sistine Chapel & St. Peter\'s Dome Climb', time: '08:30', duration: '4 hrs', operator: 'GetYourGuide', cost: 766.84 } },
  // Shore excursions (Silversea Included)
  '2026-06-24': {
    excursion: { title: 'Ruins of Herculaneum', time: '08:45', duration: '3.5 hrs', operator: 'Silversea Shore Excursion', cost: 0 },
    dining: { restaurant: 'La Dame', time: '19:30', cost: 120, status: "Erik's Birthday Celebration" },
  },
  '2026-06-25': { excursion: { title: 'Greek & Roman Taormina', time: '09:30', duration: '4 hrs', operator: 'Silversea Shore Excursion', cost: 0 } },
  '2026-06-26': {
    excursion: { title: 'Baroque Town of Noto', time: '08:45', duration: '3.5 hrs', operator: 'Silversea Shore Excursion', cost: 0 },
    dining: { restaurant: 'The Grill', time: '19:30', cost: 0, status: 'Complimentary · Open-Flame' },
  },
  '2026-06-27': { excursion: { title: 'Game of Thrones Filming Locations', time: '09:15', duration: '4 hrs', operator: 'Silversea Shore Excursion', cost: 0 } },
  '2026-06-28': { dining: { restaurant: 'Silver Note', time: '19:00', cost: 0, status: 'Complimentary · Jazz Lounge · Sea Day' } },
  '2026-06-29': { excursion: { title: 'Speedboat Adventure to Blue Cave', time: '08:30', duration: '4 hrs', operator: 'Silversea Shore Excursion', cost: 318 } },
  '2026-06-30': { excursion: { title: 'Day at the Beach Club', time: '09:00', duration: '5 hrs', operator: 'Silversea Shore Excursion', cost: 278 } },
  '2026-07-01': {
    excursion: { title: 'UNESCO World Heritage Sites (Split/Trogir)', time: '08:45', duration: '4.5 hrs', operator: 'Silversea Shore Excursion', cost: 0 },
    dining: { restaurant: 'La Terrazza', time: '19:30', cost: 0, status: 'Complimentary · Stern Windows' },
  },
  '2026-07-02': { excursion: { title: 'Zadar, Nin Salt Works & Royal Vineyards', time: '08:45', duration: '5 hrs', operator: 'Silversea Shore Excursion', cost: 0 } },
  '2026-07-03': { excursion: { title: 'Venice Guide & Boat — Private Water Taxi', time: '09:30', duration: 'Transfer', conf: 'Order #14878', operator: 'Venice Guide & Boat', cost: 350 } },
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
function typeLabel(type: string) {
  if (type === 'pre-cruise') return 'PRE-CRUISE'
  if (type === 'sea') return 'SEA DAY'
  return type.toUpperCase()
}
function formatMoney(n: number) {
  if (n === 0) return 'Included'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
}

export default function VoyageScreen() {
  const [itin, setItin] = useState<Itinerary | null>(null)
  const [bookings, setBookings] = useState<Booking[]>([])
  const [weather, setWeather] = useState<Map<string, WeatherForecast>>(new Map())
  const [error, setError] = useState(false)
  const [tab, setTab] = useState<Tab>('itinerary')
  const [expandedDate, setExpandedDate] = useState<string | null>(null)

  useEffect(() => {
    api.get<Itinerary>('/api/itinerary').then(setItin).catch(() => setError(true))
    api.get<BookingsResp>('/api/bookings').then(r => setBookings(r.bookings)).catch(() => {})
    api.get<WeatherResp>('/api/weather')
      .then(r => setWeather(new Map(r.forecasts.map(f => [f.date, f]))))
      .catch(() => {})
  }, [])

  const totalSpend = bookings.reduce((s, b) => s + b.amount_usd, 0)

  return (
    <div className="min-h-dvh bg-vault pb-24 animate-fade-in">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 border-b border-between">
        <div className="flex items-center justify-center mb-3">
          <svg className="w-6 h-6 text-gold" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="13" r="8" />
            <path d="M 12 1 L 12 5 M 12 21 L 12 25 M 1 13 L 5 13 M 23 13 L 19 13" />
          </svg>
        </div>
        <h1 className="font-display text-gold text-2xl text-center tracking-widest font-light">THE VOYAGE</h1>
      </div>

      {/* Voyage Hero */}
      {itin && (
        <div className="px-8 py-6 border-b border-between">
          <p className="text-gold font-display text-2xl text-center font-light mb-1">{itin.ship}</p>
          <p className="text-ether font-display text-base text-center font-light mb-3">{itin.route}</p>
          <p className="text-witness font-ui font-ui-xlight text-sm text-center mb-1">
            {formatDate(itin.full_journey_start)} &ndash; {formatDate(itin.ports[itin.ports.length - 1]?.date ?? itin.disembark_date)}
          </p>
          <p className="text-dusk font-ui font-ui-xlight text-sm text-center">
            {itin.full_journey_days} days &middot; {itin.cabin}
          </p>
          {itin.booking_ref && (
            <p className="text-dusk/70 font-ui font-ui-xlight text-xs text-center mt-1 tracking-wider">
              Booking {itin.booking_ref}
            </p>
          )}
        </div>
      )}

      {/* Tab Bar */}
      <div className="flex border-b border-between">
        {(['itinerary', 'bookings'] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-3 text-center font-ui font-ui-light text-xs tracking-widest uppercase transition-colors duration-300 ${
              tab === t ? 'text-gold border-b-2 border-gold' : 'text-witness hover:text-vellum'
            }`}>
            {t === 'itinerary' ? `Itinerary (${itin?.ports.length ?? 0})` : `Bookings (${bookings.length})`}
          </button>
        ))}
      </div>

      {!itin && !error && (
        <div className="px-8 py-16 text-center">
          <p className="text-dusk font-ui font-ui-light text-sm animate-pulse">Loading your voyage...</p>
        </div>
      )}
      {error && (
        <div className="px-8 py-16 text-center">
          <p className="text-witness font-ui font-ui-light text-sm">Could not load itinerary.</p>
        </div>
      )}

      {/* Itinerary Tab */}
      {tab === 'itinerary' && itin && (
        <div className="px-5 py-5 space-y-2.5">
          {itin.ports.map((port, idx) => {
            const style = TYPE_STYLES[port.type] ?? TYPE_STYLES.sea
            const w = weather.get(port.date)
            const thumb = getImage(port)
            const detail = DAY_DETAILS[port.date]
            const isExpanded = expandedDate === port.date

            return (
              <div key={idx} className={`bg-layer rounded-lg border ${style.border} overflow-hidden`}>
                {/* Tappable header */}
                <div
                  className="cursor-pointer select-none"
                  onClick={() => setExpandedDate(isExpanded ? null : port.date)}
                >
                  {/* Image strip — compact collapsed, full hero when expanded */}
                  <div className={`relative bg-vault overflow-hidden transition-all duration-400 ease-in-out ${isExpanded ? 'h-56' : 'h-24'}`}>
                    <img
                      src={thumb}
                      alt={port.name}
                      className={`w-full h-full object-cover transition-opacity duration-400 ${isExpanded ? 'opacity-90' : 'opacity-65'}`}
                      onError={e => { (e.currentTarget as HTMLImageElement).src = px(2070485) }}
                    />
                    <div className={`absolute inset-0 transition-all duration-400 ${isExpanded ? 'bg-gradient-to-t from-layer/75 via-transparent to-transparent' : 'bg-gradient-to-t from-layer/85 to-transparent'}`} />
                    <div className="absolute bottom-2.5 left-3 right-3 flex justify-between items-end">
                      <div>
                        <p className="text-vellum font-display text-sm font-light leading-tight drop-shadow">{port.name}</p>
                        {isExpanded && port.subtitle && (
                          <p className="text-vellum/70 font-ui font-ui-xlight text-xs mt-0.5 leading-snug drop-shadow">{port.subtitle}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {detail?.excursion && (
                          <span className="text-xs bg-gold/30 text-gold px-1.5 py-0.5 rounded font-bold">⛵</span>
                        )}
                        {detail?.dining && (
                          <span className="text-xs bg-ether/30 text-ether px-1.5 py-0.5 rounded font-bold">🍽</span>
                        )}
                        <span className={`${style.badge} font-ui font-ui-xlight text-xs tracking-wider uppercase px-2 py-0.5 rounded`}>
                          {typeLabel(port.type)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4">
                    <div className="flex justify-between items-center mb-1">
                      <p className="text-witness font-ui font-ui-xlight text-sm">{formatDate(port.date)}</p>
                      <div className="flex items-center gap-2">
                        {w?.forecast && (
                          <p className="text-witness font-ui font-ui-xlight text-sm">
                            {w.forecast.condition} &middot; {Math.round(w.forecast.temp_high_f)}&deg;/{Math.round(w.forecast.temp_low_f)}&deg;F
                          </p>
                        )}
                        <svg className={`w-3 h-3 text-witness/70 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </div>
                    </div>

                    {port.notes && (
                      <p className="text-vellum/80 font-ui font-ui-xlight text-sm leading-relaxed">{port.notes}</p>
                    )}
                  </div>
                </div>

                {/* Expanded detail panel */}
                {isExpanded && (
                  <div className="border-t border-between/50 px-4 pb-4 pt-3 space-y-2.5">
                    {detail?.excursion && (
                      <div className="bg-gold/5 rounded-lg p-3 border border-gold/20">
                        <p className="text-dusk font-ui font-ui-xlight text-xs tracking-wider uppercase mb-1.5">Shore Excursion</p>
                        <p className="text-vellum font-ui font-ui-light text-sm">{detail.excursion.title}</p>
                        <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1.5">
                          {detail.excursion.time && (
                            <span className="text-witness font-ui font-ui-xlight text-sm">⏱ {detail.excursion.time}</span>
                          )}
                          {detail.excursion.duration && (
                            <span className="text-witness font-ui font-ui-xlight text-sm">&middot; {detail.excursion.duration}</span>
                          )}
                          {(detail.excursion.cost ?? -1) >= 0 && (
                            <span className={`font-ui font-ui-xlight text-xs ${detail.excursion.cost === 0 ? 'text-ether' : 'text-gold'}`}>
                              {detail.excursion.cost === 0 ? 'Included' : formatMoney(detail.excursion.cost!)}
                            </span>
                          )}
                        </div>
                        {detail.excursion.operator && (
                          <p className="text-dusk font-ui font-ui-xlight text-xs mt-1">{detail.excursion.operator}</p>
                        )}
                        {detail.excursion.conf && (
                          <p className="text-dusk/70 font-ui font-ui-xlight text-xs">Conf: {detail.excursion.conf}</p>
                        )}
                      </div>
                    )}

                    {detail?.dining && (
                      <div className="bg-ether/5 rounded-lg p-3 border border-ether/20">
                        <p className="text-dusk font-ui font-ui-xlight text-xs tracking-wider uppercase mb-1.5">Dining Reservation</p>
                        <p className="text-vellum font-ui font-ui-light text-sm">{detail.dining.restaurant}</p>
                        <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1.5">
                          <span className="text-witness font-ui font-ui-xlight text-sm">{detail.dining.time}</span>
                          {(detail.dining.cost ?? 0) > 0 && (
                            <span className="text-gold font-ui font-ui-xlight text-xs">{formatMoney(detail.dining.cost!)}</span>
                          )}
                          {detail.dining.status && (
                            <span className="text-witness font-ui font-ui-xlight text-xs uppercase tracking-wide">{detail.dining.status}</span>
                          )}
                        </div>
                      </div>
                    )}

                    {w?.forecast && (
                      <div className="rounded-lg p-3 border border-between/50 bg-between/20">
                        <p className="text-dusk font-ui font-ui-xlight text-xs tracking-wider uppercase mb-2">Weather Detail</p>
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <p className="text-vellum font-ui font-ui-light text-sm">
                              {Math.round(w.forecast.temp_high_f)}&deg; / {Math.round(w.forecast.temp_low_f)}&deg;
                            </p>
                            <p className="text-dusk font-ui font-ui-xlight text-xs">Hi / Lo °F</p>
                          </div>
                          <div>
                            <p className="text-vellum font-ui font-ui-light text-sm">{w.forecast.condition}</p>
                            <p className="text-dusk font-ui font-ui-xlight text-xs">Sky</p>
                          </div>
                          <div>
                            <p className="text-vellum font-ui font-ui-light text-sm">{w.forecast.wind_max_mph} mph</p>
                            <p className="text-dusk font-ui font-ui-xlight text-xs">Wind</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {!detail && !w?.forecast && (
                      <p className="text-dusk font-ui font-ui-xlight text-xs text-center py-1">No additional details on file</p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Bookings Tab */}
      {tab === 'bookings' && (
        <div className="px-5 py-5">
          <div className="bg-layer rounded-xl p-5 border border-gold/30 mb-4 text-center"
            style={{ boxShadow: '0 0 20px rgba(232, 192, 122, 0.06)' }}>
            <p className="text-witness font-ui font-ui-xlight text-xs tracking-widest uppercase mb-1">Total Investment</p>
            <p className="text-gold font-display text-3xl font-light">{formatMoney(totalSpend)}</p>
            <p className="text-dusk font-ui font-ui-xlight text-xs mt-1">
              {bookings.filter(b => b.status === 'paid in full').length > 0
                ? `${bookings.filter(b => b.status === 'paid in full').length} paid in full · ${bookings.filter(b => b.status === 'confirmed').length} confirmed`
                : `All ${bookings.length} confirmed`
              }
            </p>
          </div>
          <div className="space-y-2.5">
            {bookings.map((b, idx) => (
              <div key={idx} className="bg-layer rounded-lg p-4 border border-between hover:bg-hover transition-colors duration-300">
                <div className="flex items-start gap-3">
                  <span className={`${BOOKING_COLORS[b.type] ?? 'text-dusk'} font-ui font-ui-xlight text-xs tracking-wider uppercase bg-hover px-2 py-0.5 rounded shrink-0 mt-0.5`}>
                    {b.type}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-vellum font-ui font-ui-light text-sm leading-snug">{b.description}</p>
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-witness font-ui font-ui-xlight text-xs">{b.confirmation}</span>
                      <span className={`font-ui font-ui-xlight text-xs ${b.status === 'paid in full' ? 'text-gold' : 'text-dusk'}`}>
                        {b.amount_usd > 0 ? formatMoney(b.amount_usd) : 'Included'}
                      </span>
                    </div>
                    <span className={`inline-block mt-1 font-ui font-ui-xlight text-xs tracking-wider uppercase px-2 py-0.5 rounded ${
                      b.status === 'paid in full' ? 'bg-gold/15 text-gold' : 'bg-ether/15 text-ether'
                    }`}>
                      {b.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  )
}
